"""统一处理 HTTP 请求和限速控制。

所有外部页面访问都应通过本模块进入，避免出现某些调用绕过统一请求控制。
当前版本只提供同步请求能力，后续如果要扩展异步抓取，也应保留相同的合规入口。
"""

from __future__ import annotations

import random
import re
import threading
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from crawler.models import FetchResult, RateLimitConfig


class Fetcher:
    """带有限速控制的统一请求器。"""

    def __init__(
        self,
        default_rate_limit: RateLimitConfig,
        domain_rate_limits: dict[str, RateLimitConfig],
    ) -> None:
        self.default_rate_limit = default_rate_limit
        self.domain_rate_limits = domain_rate_limits
        self._last_request_at: dict[str, float] = {}
        self._rate_limit_lock = threading.Lock()

    def _resolve_rate_limit(self, url: str) -> RateLimitConfig:
        """根据 URL 域名选择限速配置。"""

        host = self._normalized_host(url)
        if host in self.domain_rate_limits:
            return self.domain_rate_limits[host]

        matched_domain = ""
        matched_config = self.default_rate_limit
        for domain, config in self.domain_rate_limits.items():
            normalized_domain = domain.lower()
            if host == normalized_domain or host.endswith(f".{normalized_domain}"):
                if len(normalized_domain) > len(matched_domain):
                    matched_domain = normalized_domain
                    matched_config = config
        return matched_config

    def _respect_rate_limit(self, url: str, rate_limit: RateLimitConfig) -> None:
        """按域名级限速要求等待。

        这里使用随机区间而不是固定秒数，是为了避免多来源批量任务形成稳定访问节奏。
        """

        domain = self._normalized_host(url)
        with self._rate_limit_lock:
            now = time.monotonic()
            delay_seconds = random.uniform(
                rate_limit.min_interval_seconds,
                rate_limit.max_interval_seconds,
            )
            previous = self._last_request_at.get(domain)

            if previous is not None:
                elapsed = now - previous
                if elapsed < delay_seconds:
                    time.sleep(delay_seconds - elapsed)

            self._last_request_at[domain] = time.monotonic()

    def fetch(self, url: str) -> FetchResult:
        """抓取单个公开页面。

        返回:
        - 无论成功、失败还是被限流拒绝，都会返回 `FetchResult`。
        """

        rate_limit = self._resolve_rate_limit(url)
        self._respect_rate_limit(url, rate_limit)

        headers = self._build_headers(url, rate_limit)

        try:
            response_data = self._request_with_available_client(url, headers)
            redirect_target = ""
            if self._is_html_response(
                content_type=str(response_data["content_type"]),
                url=str(response_data["final_url"]),
            ):
                redirect_target = self._extract_client_side_redirect(
                    current_url=url,
                    html_text=str(response_data["text"]),
                )
            if redirect_target:
                response_data = self._request_with_available_client(redirect_target, headers)
            if self._is_waf_blocked_response(response_data) and self._should_retry_with_browser(url):
                browser_response = self._request_with_playwright(url)
                if browser_response is not None:
                    response_data = browser_response
        except Exception as exc:
            return FetchResult(
                url=url,
                status_code=None,
                content_type="",
                text="",
                final_url=url,
                fetched_at=datetime.utcnow(),
                success=False,
                failure_reason=f"请求失败: {exc}",
                body_bytes=b"",
            )

        if self._is_waf_blocked_response(response_data):
            return FetchResult(
                url=url,
                status_code=response_data["status_code"],
                content_type=response_data["content_type"],
                text="",
                final_url=response_data["final_url"],
                fetched_at=datetime.utcnow(),
                success=False,
                failure_reason="WAF阻断",
                body_bytes=bytes(response_data["body_bytes"]),
            )

        if response_data["status_code"] in {403, 429, 503}:
            return FetchResult(
                url=url,
                status_code=response_data["status_code"],
                content_type=response_data["content_type"],
                text="",
                final_url=response_data["final_url"],
                fetched_at=datetime.utcnow(),
                success=False,
                failure_reason=f"服务端拒绝访问，状态码 {response_data['status_code']}",
                body_bytes=bytes(response_data["body_bytes"]),
            )

        return FetchResult(
            url=url,
            status_code=response_data["status_code"],
            content_type=response_data["content_type"],
            text=response_data["text"],
            final_url=response_data["final_url"],
            fetched_at=datetime.utcnow(),
            success=200 <= response_data["status_code"] < 300,
            failure_reason="" if 200 <= response_data["status_code"] < 300 else f"HTTP {response_data['status_code']}",
            body_bytes=bytes(response_data["body_bytes"]),
        )

    def post_json(self, url: str, payload: dict[str, object]) -> FetchResult:
        """按统一限速发送 JSON POST 请求。"""

        rate_limit = self._resolve_rate_limit(url)
        self._respect_rate_limit(url, rate_limit)
        headers = self._build_headers(url, rate_limit)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json,text/plain,*/*"

        try:
            import httpx

            with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
                response = client.post(url, json=payload)
            text = response.text
            body_bytes = response.content
            success = 200 <= response.status_code < 300
            return FetchResult(
                url=url,
                status_code=response.status_code,
                content_type=response.headers.get("Content-Type", ""),
                text=text,
                final_url=str(response.url),
                fetched_at=datetime.utcnow(),
                success=success,
                failure_reason="" if success else f"HTTP {response.status_code}",
                body_bytes=body_bytes,
            )
        except Exception as exc:
            return FetchResult(
                url=url,
                status_code=None,
                content_type="",
                text="",
                final_url=url,
                fetched_at=datetime.utcnow(),
                success=False,
                failure_reason=f"请求失败: {exc}",
                body_bytes=b"",
            )

    def _normalized_host(self, url: str) -> str:
        """返回不含端口的 hostname，便于同一站点的子域限速匹配。"""

        return (urlparse(url).hostname or "").lower()

    def _build_headers(self, url: str, rate_limit: RateLimitConfig) -> dict[str, str]:
        """构造接近正常浏览器导航的请求头。"""

        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        headers = {
            "User-Agent": rate_limit.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.8,*/*;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
        if origin:
            headers["Referer"] = f"{origin}/"
        if parsed.hostname and parsed.hostname.endswith("ems.com.cn"):
            headers.update(
                {
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-User": "?1",
                }
            )
        return headers

    def _is_waf_blocked_response(self, response_data: dict[str, str | int | bytes]) -> bool:
        """识别站点安全设备返回的阻断页。"""

        status_code = int(response_data["status_code"])
        text = str(response_data.get("text", ""))
        final_url = str(response_data.get("final_url", "")).lower()
        waf_markers = [
            "访问的url有可能对网站造成安全威胁",
            "your request has been blocked",
            "potential threats to the server",
            "attack.jinxibei.com",
        ]
        lowered_text = text.lower()
        if any(marker.lower() in lowered_text for marker in waf_markers):
            return True
        return status_code in {405, 406, 412} and "ems.com.cn" in final_url

    def _should_retry_with_browser(self, url: str) -> bool:
        """只有公开 EMS 页面被安全页阻断时，才尝试浏览器会话。"""

        return self._normalized_host(url).endswith("ems.com.cn")

    def _is_html_response(self, content_type: str, url: str) -> bool:
        """判断响应是否应按 HTML 处理。"""

        lowered_type = content_type.lower()
        lowered_url = url.lower()
        return "html" in lowered_type or lowered_url.endswith((".html", ".htm", "/"))

    def _request_with_available_client(
        self,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, str | int | bytes]:
        """优先使用 httpx，请求库缺失时退回到 urllib。

        这样可以减少环境依赖带来的运行失败，尤其适合第一版原型。
        """

        try:
            import httpx

            with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
            content_type = response.headers.get("Content-Type", "")
            body_bytes = response.content
            text = self._decode_response_body(
                body_bytes=body_bytes,
                content_type=content_type,
                final_url=str(response.url),
                apparent_encoding=response.encoding,
            )
            return {
                "status_code": response.status_code,
                "content_type": content_type,
                "text": text,
                "final_url": str(response.url),
                "body_bytes": body_bytes,
            }
        except ModuleNotFoundError:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=20.0) as response:
                raw_body = response.read()
                content_type = response.headers.get("Content-Type", "")
                text = self._decode_response_body(
                    body_bytes=raw_body,
                    content_type=content_type,
                    final_url=response.geturl(),
                    apparent_encoding=response.headers.get_content_charset(),
                )
                return {
                    "status_code": response.status,
                    "content_type": content_type,
                    "text": text,
                    "final_url": response.geturl(),
                    "body_bytes": raw_body,
                }

    def _request_with_playwright(self, url: str) -> dict[str, str | int | bytes] | None:
        """用真实浏览器慢速重试被 EMS WAF 拦截的公开页面。

        Playwright 是可选依赖。未安装或浏览器未初始化时返回 `None`，
        调用方继续保留原始 HTTP 失败结果。
        """

        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError:
            return None

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    user_agent=self.default_rate_limit.user_agent,
                    extra_http_headers={
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
                    },
                )
                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(random.randint(1200, 2500))
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except PlaywrightTimeoutError:
                    pass

                final_url = page.url
                content = page.content()
                body_bytes = content.encode("utf-8")
                status_code = response.status if response is not None else 200
                content_type = (
                    response.headers.get("content-type", "text/html; charset=utf-8")
                    if response is not None
                    else "text/html; charset=utf-8"
                )
                context.close()
                browser.close()
                return {
                    "status_code": status_code,
                    "content_type": content_type,
                    "text": content,
                    "final_url": final_url,
                    "body_bytes": body_bytes,
                }
        except PlaywrightError:
            return None

    def _decode_response_body(
        self,
        body_bytes: bytes,
        content_type: str,
        final_url: str,
        apparent_encoding: str | None,
    ) -> str:
        """根据响应类型决定是否解码正文。

        HTML 和纯文本正文会被解码后继续进入链接发现与页面解析。
        PDF 等二进制内容保留原始字节，由后续专门解析器处理。
        """

        lowered_type = content_type.lower()
        lowered_url = final_url.lower()
        if "pdf" in lowered_type or lowered_url.endswith(".pdf"):
            return ""

        if not body_bytes:
            return ""

        charset = apparent_encoding or "utf-8"
        return body_bytes.decode(charset, errors="replace")

    def _extract_client_side_redirect(self, current_url: str, html_text: str) -> str:
        """识别简单的前端跳转脚本或 meta refresh。

        某些首页返回 200，但实际正文只是一个跳转脚本。
        这里先处理最常见的几种写法，避免首页内容为空。
        """

        js_patterns = [
            r"""window\.location\.replace\(['"]([^'"]+)['"]\)""",
            r"""window\.location\.href\s*=\s*['"]([^'"]+)['"]""",
            r"""location\.href\s*=\s*['"]([^'"]+)['"]""",
        ]
        for pattern in js_patterns:
            match = re.search(pattern, html_text, flags=re.IGNORECASE)
            if match:
                return urljoin(current_url, match.group(1))

        meta_match = re.search(
            r"""http-equiv=["']refresh["'][^>]*content=["'][^;]+;\s*url=([^"']+)["']""",
            html_text,
            flags=re.IGNORECASE,
        )
        if meta_match:
            return urljoin(current_url, meta_match.group(1).strip())

        return ""
