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
    "claim",
    "insurance",
    "liability",
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
    "理赔",
    "赔付",
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
    "support",
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


def is_policy_like_url(source_base_url: str, url: str, anchor_text: str) -> bool:
    """根据 URL 和锚文本联合判断候选页面。"""

    source_domain = urlparse(source_base_url).netloc.lower()
    parsed = urlparse(url)
    if parsed.netloc.lower() != source_domain:
        return False

    lowered = url.lower()
    if any(lowered.endswith(suffix) for suffix in STATIC_FILE_SUFFIXES):
        return False

    if "/xhtml/" in lowered or "/images/" in lowered or "/libs/" in lowered:
        return False

    if any(keyword in lowered for keyword in NEGATIVE_HINT_KEYWORDS):
        return False

    anchor_lower = anchor_text.lower()
    if any(keyword in anchor_lower for keyword in NEGATIVE_HINT_KEYWORDS):
        return False

    return any(keyword in lowered for keyword in POLICY_HINT_KEYWORDS) or any(
        keyword in anchor_lower for keyword in POLICY_HINT_KEYWORDS
    )


def discover_policy_links(source_base_url: str, html_text: str) -> list[str]:
    """提取并过滤候选政策链接。"""

    discovered: list[str] = []
    seen: set[str] = set()
    for link, anchor_text in extract_links(source_base_url, html_text):
        if link in seen:
            continue
        if not is_policy_like_url(source_base_url, link, anchor_text):
            continue
        seen.add(link)
        discovered.append(link)
    return discovered
