"""解析 HTML 文本，提取基础政策信息。

当前实现只做通用文本抽取和主题判断，不写站点定制逻辑。
后续如果某个站点结构复杂，应新增专门解析器，而不是把条件堆到本文件中。
"""

from __future__ import annotations

import re
from html import unescape

from crawler.insurance_parser import parse_insurance_terms
from crawler.models import FilteredPageRecord, PolicyRecord, SourceConfig

POLICY_SIGNAL_KEYWORDS = [
    "禁寄",
    "限寄",
    "规则",
    "条款",
    "协议",
    "理赔",
    "赔付",
    "保价",
    "保险",
    "声明价值",
    "清关",
    "海关",
    "危险品",
    "锂电池",
    "冷链",
    "包装",
    "寄件须知",
    "prohibited",
    "restricted",
    "terms",
    "liability",
    "claim",
    "dangerous goods",
    "customs",
]

NOISE_HINTS = [
    "登录",
    "注册",
    "搜索",
    "首页",
    "购物车",
    "立即下单",
    "个人中心",
    "login",
    "register",
    "sign in",
    "track",
    "联系我们",
    "关于我们",
    "新闻中心",
    "加入我们",
    "个人服务",
    "企业服务",
    "运单查询",
    "网点查询",
    "价格时效",
    "快递服务",
    "快运服务",
    "解决方案",
    "customer service",
    "contact us",
    "help & support",
    "our company",
    "careers",
    "support",
    "locations",
]

HARD_POLICY_TITLE_HINTS = [
    "条款",
    "协议",
    "禁寄",
    "限寄",
    "restricted",
    "prohibited",
    "dangerous goods",
    "hazmat",
    "customs",
    "claim",
    "liability",
    "赔付",
    "理赔",
    "保价",
]


def _strip_html_tags(html_text: str) -> str:
    """用简单正则去除 HTML 标签。

    当前阶段先提供无依赖的基础实现，后续可以替换为 `BeautifulSoup`
    或 `trafilatura` 等更稳定的正文抽取方案。
    """

    text = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(unescape(text).split())


def _guess_categories(text: str, allowed_topics: list[str]) -> list[str]:
    """根据关键词粗略判断页面主题。"""

    matches: list[str] = []
    keyword_map = {
        "禁限寄": ["禁寄", "限寄", "禁止寄递", "违禁品"],
        "危险品": ["危险品", "危险货物", "锂电池", "易燃", "腐蚀"],
        "冷链": ["冷链", "冷藏", "冷冻", "温控", "干冰"],
        "国际清关": ["清关", "报关", "海关", "商业发票", "关税"],
        "邮寄保险": ["保险", "保价", "声明价值", "liability"],
        "保价赔付": ["赔付", "理赔", "索赔", "免责条款"],
    }

    for category in allowed_topics:
        if category not in keyword_map:
            continue
        if any(keyword.lower() in text.lower() for keyword in keyword_map[category]):
            matches.append(category)

    return matches or ["服务条款"]


def _extract_title(html_text: str, company: str) -> str:
    """优先提取页面 title，没有时回退到公司名。"""

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not title_match:
        return company
    title = " ".join(unescape(title_match.group(1)).split())
    return title or company


def _extract_published_at(text: str) -> str:
    """从正文中提取发布日期或更新时间。"""

    patterns = [
        r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(20\d{2}\.\d{1,2}\.\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _build_summary(text: str) -> str:
    """生成较短摘要，避免把整页导航都带进展示结果。"""

    sentences = re.split(r"[。！？.!?]", text)
    useful_parts = [part.strip() for part in sentences if len(part.strip()) >= 12]
    summary = "。".join(useful_parts[:3]).strip()
    if summary:
        return summary[:300]
    return text[:300]


def _count_policy_signals(text: str, title: str) -> int:
    """统计页面中与政策规则相关的信号词数量。"""

    combined = f"{title} {text}".lower()
    return sum(1 for keyword in POLICY_SIGNAL_KEYWORDS if keyword.lower() in combined)


def _is_noise_page(title: str, summary: str) -> bool:
    """粗略排除首页导航、登录注册、纯跳转等噪声页面。"""

    combined = f"{title} {summary}".lower()
    noise_hits = sum(1 for keyword in NOISE_HINTS if keyword.lower() in combined)
    return noise_hits >= 3


def _has_hard_policy_title(title: str) -> bool:
    """标题中是否包含强政策语义。"""

    lowered = title.lower()
    return any(keyword.lower() in lowered for keyword in HARD_POLICY_TITLE_HINTS)


def _looks_like_navigation_page(text: str, summary: str) -> bool:
    """通过重复菜单词判断页面是否更像导航聚合页。"""

    combined = f"{text[:1500]} {summary}".lower()
    menu_tokens = [
        "首页",
        "产品与服务",
        "个人服务",
        "企业服务",
        "在线寄件",
        "运单查询",
        "网点查询",
        "价格时效",
        "登录",
        "注册",
        "home",
        "services",
        "support",
        "menu",
        "contact",
        "locations",
    ]
    hits = sum(1 for token in menu_tokens if token.lower() in combined)
    return hits >= 6


def _build_filtered_record(
    source: SourceConfig,
    url: str,
    title: str,
    reason: str,
    summary: str,
) -> FilteredPageRecord:
    """构造被过滤页面的审计记录。"""

    return FilteredPageRecord(
        source_id=source.source_id,
        company=source.company,
        url=url,
        title=title,
        filter_reason=reason,
        summary=summary[:300],
    )


def parse_policy_page(
    source: SourceConfig,
    url: str,
    html_text: str,
) -> tuple[PolicyRecord | None, FilteredPageRecord | None]:
    """把 HTML 页面转换为政策记录，或给出过滤原因。

    返回:
    - `(PolicyRecord, None)` 表示页面通过筛选，可作为结构化样本保存。
    - `(None, FilteredPageRecord)` 表示页面质量不足，只做审计记录，不进入训练样本。
    """

    plain_text = _strip_html_tags(html_text)
    title = _extract_title(html_text, source.company)
    summary = _build_summary(plain_text)
    policy_categories = _guess_categories(plain_text, source.allowed_topics)
    policy_signals = _count_policy_signals(plain_text, title)

    if len(plain_text) < 120:
        return None, _build_filtered_record(source, url, title, "正文过短", summary)

    if _is_noise_page(title, summary):
        return None, _build_filtered_record(source, url, title, "页面噪声过高", summary)

    if _looks_like_navigation_page(plain_text, summary) and not _has_hard_policy_title(title):
        return None, _build_filtered_record(source, url, title, "导航页特征过强", summary)

    if policy_signals < 3 and not _has_hard_policy_title(title):
        return None, _build_filtered_record(source, url, title, "政策信号不足", summary)

    if policy_signals < 2 and policy_categories == ["服务条款"]:
        return None, _build_filtered_record(source, url, title, "政策信号不足", summary)

    insurance_info = parse_insurance_terms(plain_text)

    return PolicyRecord(
        source_id=source.source_id,
        company=source.company,
        url=url,
        title=title,
        published_at=_extract_published_at(plain_text),
        policy_categories=policy_categories,
        summary=summary,
        evidence_text=summary,
        insurance_available=insurance_info["insurance_available"],
        insurance_type=insurance_info["insurance_type"],
        compensation_limit=insurance_info["compensation_limit"],
        claim_deadline=insurance_info["claim_deadline"],
        requirements=insurance_info["requirements"],
        insurance_exclusions=insurance_info["insurance_exclusions"],
    ), None
