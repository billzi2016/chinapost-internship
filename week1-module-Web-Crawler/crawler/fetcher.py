"""统一处理 HTTP 请求、限速和 robots 校验。

所有外部页面访问都应通过本模块进入，避免出现某些调用绕过合规控制。
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
from crawler.robots import RobotsManager


class Fetcher:
    """带有 robots 和限速控制的统一请求器。"""

    def __init__(
        self,
        robots_manager: RobotsManager,
        default_rate_limit: RateLimitConfig,
        domain_rate_limits: dict[str, RateLimitConfig],
    ) -> None:
        self.robots_manager = robots_manager
        self.default_rate_limit = default_rate_limit
        self.domain_rate_limits = domain_rate_limits
        self._last_request_at: dict[str, float] = {}
        self._rate_limit_lock = threading.Lock()

    def _resolve_rate_limit(self, url: str) -> RateLimitConfig:
        """根据 URL 域名选择限速配置。"""

        domain = urlparse(url).netloc
        return self.domain_rate_limits.get(domain, self.default_rate_limit)

    def _respect_rate_limit(self, url: str, rate_limit: RateLimitConfig) -> None:
        """按域名级限速要求等待。

        这里使用随机区间而不是固定秒数，是为了避免多来源批量任务形成稳定访问节奏。
        """

        domain = urlparse(url).netloc
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
        - 无论成功、失败还是被 robots 拒绝，都会返回 `FetchResult`。
        """

        rate_limit = self._resolve_rate_limit(url)
        robots_decision = self.robots_manager.is_allowed(url, rate_limit.user_agent)
        if not robots_decision.allowed:
            return FetchResult(
                url=url,
                status_code=None,
                content_type="",
                text="",
                final_url=url,
                fetched_at=datetime.utcnow(),
                success=False,
                robots_allowed=robots_decision.allowed,
                robots_reason=robots_decision.reason,
                failure_reason=robots_decision.reason,
            )

        self._respect_rate_limit(url, rate_limit)

        headers = {
            "User-Agent": rate_limit.user_agent,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/pdf,application/xhtml+xml",
        }

        try:
            response_data = self._request_with_available_client(url, headers)
            redirect_target = self._extract_client_side_redirect(
                current_url=url,
                html_text=str(response_data["text"]),
            )
            if redirect_target:
                response_data = self._request_with_available_client(redirect_target, headers)
        except Exception as exc:
            return FetchResult(
                url=url,
                status_code=None,
                content_type="",
                text="",
                final_url=url,
                fetched_at=datetime.utcnow(),
                success=False,
                robots_allowed=robots_decision.allowed,
                robots_reason=robots_decision.reason,
                failure_reason=f"请求失败: {exc}",
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
                robots_allowed=robots_decision.allowed,
                robots_reason=robots_decision.reason,
                failure_reason=f"服务端拒绝访问，状态码 {response_data['status_code']}",
            )

        return FetchResult(
            url=url,
            status_code=response_data["status_code"],
            content_type=response_data["content_type"],
            text=response_data["text"],
            final_url=response_data["final_url"],
            fetched_at=datetime.utcnow(),
            success=200 <= response_data["status_code"] < 300,
            robots_allowed=robots_decision.allowed,
            robots_reason=robots_decision.reason,
            failure_reason="" if 200 <= response_data["status_code"] < 300 else f"HTTP {response_data['status_code']}",
        )

    def _request_with_available_client(
        self,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, str | int]:
        """优先使用 httpx，请求库缺失时退回到 urllib。

        这样可以减少环境依赖带来的运行失败，尤其适合第一版原型。
        """

        try:
            import httpx

            with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
            return {
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "text": response.text,
                "final_url": str(response.url),
            }
        except ModuleNotFoundError:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=20.0) as response:
                raw_body = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                text = raw_body.decode(charset, errors="replace")
                return {
                    "status_code": response.status,
                    "content_type": response.headers.get("Content-Type", ""),
                    "text": text,
                "final_url": response.geturl(),
            }

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
