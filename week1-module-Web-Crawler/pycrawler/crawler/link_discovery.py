"""从页面中发现候选政策链接。

本模块只负责链接提取、规范化和过滤，不负责任何抓取动作。
把这部分单独拆出来，是为了避免调度器同时承担队列控制和 HTML 细节处理。
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from crawler.dedupe import canonicalize_url


POLICY_HINT_KEYWORDS = [
    "policy",
    "terms",
    "insurance",
    "customs",
    "dangerous-goods",
    "hazmat",
    "restricted",
    "prohibited",
    "guide",
    "notice",
    "rules",
    "保价",
    "保险",
    "寄件",
    "须知",
    "禁寄",
    "限寄",
    "规则",
    "条款",
    "协议",
    "海关",
    "清关",
    "冷链",
    "危险品",
]

STATIC_FILE_SUFFIXES = {
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
    ".xml",
    ".json",
    ".zip",
    ".rar",
    ".7z",
}

NEGATIVE_HINT_KEYWORDS = [
    "login",
    "register",
    "sign-in",
    "search",
    "query",
    "track",
    "tracking",
    "order",
    "cart",
    "download-app",
    "app下载",
    "登录",
    "注册",
    "查询",
    "下单",
    "contact",
    "customer-service",
    "service-alert",
    "news",
    "media",
    "about",
    "careers",
    "portal",
    "帮助中心",
    "联系我们",
    "关于我们",
    "新闻中心",
    "通知公告",
]

PATH_POLICY_HINT_KEYWORDS = [
    "terms",
    "insurance",
    "customs",
    "dangerous-goods",
    "hazmat",
    "restricted",
    "prohibited",
    "rules",
    "policy",
    "保价",
    "保险",
    "寄件",
    "须知",
    "禁寄",
    "限寄",
    "规则",
    "条款",
    "协议",
    "海关",
    "清关",
    "冷链",
    "危险品",
]


def extract_links(base_url: str, html_text: str) -> list[tuple[str, str]]:
    """从 HTML 中提取链接和锚文本。"""

    pattern = re.compile(
        r"""<a[^>]*href\s*=\s*["']([^"'#]+)["'][^>]*>(.*?)</a>""",
        flags=re.IGNORECASE | re.DOTALL,
    )
    extracted: list[tuple[str, str]] = []
    for href, inner_html in pattern.findall(html_text):
        if href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absolute_url = canonicalize_url(urljoin(base_url, href))
        anchor_text = " ".join(re.sub(r"<[^>]+>", " ", inner_html).split())
        extracted.append((absolute_url, anchor_text))
    return extracted


def _is_allowed_domain(url: str, allowed_domains: list[str]) -> bool:
    """判断链接是否落在允许域名范围内。"""

    target_domain = urlparse(url).netloc.lower()
    if not target_domain:
        return False

    normalized_domains = [domain.lower() for domain in allowed_domains if domain]
    if not normalized_domains:
        return True

    return any(
        target_domain == domain or target_domain.endswith(f".{domain}")
        for domain in normalized_domains
    )


def is_policy_like_url(
    source_base_url: str,
    url: str,
    anchor_text: str,
    allowed_domains: list[str] | None = None,
) -> bool:
    """根据 URL 和锚文本联合判断候选页面。"""

    source_domain = urlparse(source_base_url).hostname or ""
    target_domain = urlparse(url).hostname or ""
    if allowed_domains is None:
        if target_domain.lower() != source_domain.lower():
            return False
        allowed_domain_list = [source_domain]
    else:
        allowed_domain_list = list(allowed_domains)
        if source_domain and source_domain not in allowed_domain_list:
            allowed_domain_list.append(source_domain)

    if not _is_allowed_domain(url, allowed_domain_list):
        return False

    lowered = url.lower()
    is_pdf = lowered.endswith(".pdf")
    if any(lowered.endswith(suffix) for suffix in STATIC_FILE_SUFFIXES):
        return False

    if "/xhtml/" in lowered or "/images/" in lowered or "/libs/" in lowered:
        return False

    if any(keyword in lowered for keyword in NEGATIVE_HINT_KEYWORDS):
        return False

    anchor_lower = anchor_text.lower()
    if any(keyword in anchor_lower for keyword in NEGATIVE_HINT_KEYWORDS):
        return False

    path_has_policy_hint = any(keyword in lowered for keyword in PATH_POLICY_HINT_KEYWORDS)
    anchor_has_policy_hint = any(keyword in anchor_lower for keyword in POLICY_HINT_KEYWORDS)
    hard_anchor_hit = any(
        keyword in anchor_lower
        for keyword in [
            "条款",
            "协议",
            "禁寄",
            "限寄",
            "规则",
            "须知",
            "保价",
            "保险",
            "赔偿",
            "海关",
            "清关",
            "dangerous goods",
            "restricted",
            "prohibited",
            "customs",
        ]
    )

    if is_pdf:
        return path_has_policy_hint or anchor_has_policy_hint

    if path_has_policy_hint:
        return True

    return hard_anchor_hit and anchor_has_policy_hint


def discover_policy_links(
    source_base_url: str,
    html_text: str,
    allowed_domains: list[str] | None = None,
) -> list[str]:
    """提取并过滤候选政策链接。"""

    discovered: list[str] = []
    seen: set[str] = set()
    for link, anchor_text in extract_links(source_base_url, html_text):
        if link in seen:
            continue
        if not is_policy_like_url(source_base_url, link, anchor_text, allowed_domains):
            continue
        seen.add(link)
        discovered.append(link)
    return discovered
