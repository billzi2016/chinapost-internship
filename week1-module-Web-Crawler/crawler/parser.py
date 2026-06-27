"""解析 HTML 文本，提取基础政策信息。

当前实现只做通用文本抽取和主题判断，不写站点定制逻辑。
后续如果某个站点结构复杂，应新增专门解析器，而不是把条件堆到本文件中。
"""

from __future__ import annotations

import re
from html import unescape
from pathlib import Path

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
    "产品介绍",
    "产品服务",
    "时限",
    "资费",
    "收费",
    "费用",
    "承诺服务",
    "服务范围",
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
    "须知",
    "规范",
    "标准",
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

GENERIC_POLICY_CATEGORY = "服务条款"


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
        "保价赔付": ["赔付", "理赔", "索赔", "赔偿", "免责条款"],
        "服务条款": ["服务条款", "使用条款", "terms", "conditions", "agreement", "协议"],
        "包装要求": ["包装要求", "包装规范", "包装须知", "packaging"],
        "产品服务": ["产品介绍", "产品服务", "产品范围", "承诺服务", "开办范围"],
        "时限标准": ["时限", "时效", "当日送达", "次日递", "承诺服务"],
        "资费规则": ["资费", "收费", "费用", "价格", "报价"],
    }

    for category in allowed_topics:
        if category not in keyword_map:
            continue
        if any(keyword.lower() in text.lower() for keyword in keyword_map[category]):
            matches.append(category)

    if matches:
        return matches

    lowered = text.lower()
    generic_terms = keyword_map[GENERIC_POLICY_CATEGORY]
    if any(keyword.lower() in lowered for keyword in generic_terms):
        return [GENERIC_POLICY_CATEGORY]
    return []


def _extract_title(html_text: str, company: str) -> str:
    """优先提取页面 title，没有时回退到公司名。"""

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not title_match:
        return company
    title = " ".join(unescape(title_match.group(1)).split())
    return title or company


def _extract_pdf_title(url: str, company: str) -> str:
    """从 PDF URL 推导标题，避免原始文件名完全丢失语义。"""

    filename = Path(url.split("?", 1)[0]).name
    if not filename:
        return f"{company} PDF"
    return unescape(filename)


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


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """统计关键字命中次数。"""

    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def _count_policy_signals(text: str, title: str) -> int:
    """统计页面中与政策规则相关的信号词数量。"""

    combined = f"{title} {text}".lower()
    return sum(1 for keyword in POLICY_SIGNAL_KEYWORDS if keyword.lower() in combined)


def _count_noise_hits(title: str, summary: str) -> int:
    """统计噪声页命中词数量。"""

    combined = f"{title} {summary}".lower()
    return sum(1 for keyword in NOISE_HINTS if keyword.lower() in combined)


def _is_noise_page(title: str, summary: str) -> bool:
    """粗略排除首页导航、登录注册、纯跳转等噪声页面。"""

    return _count_noise_hits(title, summary) >= 3


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


def _looks_like_homepage(url: str, title: str, summary: str) -> bool:
    """识别官网首页或强导航首页。"""

    normalized_url = url.rstrip("/")
    homepage_path = normalized_url.count("/") <= 2
    homepage_title = any(token in title for token in ["首页", "Home"])
    menu_heavy = _count_noise_hits(title, summary) >= 4
    return homepage_path and (homepage_title or menu_heavy)


def _looks_like_blocked_or_utility_page(url: str, title: str, plain_text: str) -> str:
    """识别安全阻断、登录、报价和客服导航等工具页。"""

    lowered_url = url.lower()
    combined = f"{title} {plain_text[:2500]}".lower()

    waf_markers = [
        "访问的url有可能对网站造成安全威胁",
        "your request has been blocked",
        "potential threats to the server",
        "attack.jinxibei.com",
    ]
    if any(marker.lower() in combined for marker in waf_markers):
        return "WAF阻断页"

    login_markers = ["个人登录", "法人/经办人登录", "用户名", "密码", "验证码", "忘记密码"]
    if "login" in lowered_url or sum(1 for marker in login_markers if marker in combined) >= 4:
        return "登录页"

    quote_markers = ["报价查询", "发件人省份", "寄达国", "业务产品", "总资费", "首重资费"]
    if "toquoteindex" in lowered_url or sum(1 for marker in quote_markers if marker in combined) >= 4:
        return "报价工具页"

    service_nav_markers = [
        "11183在线客服",
        "欢迎使用11183在线客服中心",
        "扫描二维码关注",
        "自助服务",
        "查邮件",
        "寄快递",
        "查时限",
        "查资费",
        "查邮编",
        "自提点",
    ]
    if sum(1 for marker in service_nav_markers if marker.lower() in combined) >= 6:
        return "客服导航页"

    return ""


def _has_meaningful_policy_category(categories: list[str]) -> bool:
    """判断是否命中了非回退型主题。"""

    return any(category != GENERIC_POLICY_CATEGORY for category in categories)


def _looks_like_policy_content(
    url: str,
    title: str,
    summary: str,
    plain_text: str,
    categories: list[str],
    policy_signals: int,
) -> tuple[bool, str]:
    """集中判断页面是否足够像真实政策内容。"""

    has_hard_title = _has_hard_policy_title(title)
    meaningful_category = _has_meaningful_policy_category(categories)
    insurance_hits = _count_keyword_hits(
        plain_text,
        ["保价", "声明价值", "shipment insurance", "declared value", "liability", "claim"],
    )
    utility_reason = _looks_like_blocked_or_utility_page(url, title, plain_text)
    if utility_reason:
        return False, utility_reason

    if len(plain_text) < 120 and policy_signals < 4 and not has_hard_title and not meaningful_category:
        return False, "正文过短"

    if _looks_like_homepage(url, title, summary) and not has_hard_title:
        return False, "首页导航特征过强"

    if _is_noise_page(title, summary) and not has_hard_title:
        return False, "页面噪声过高"

    if _looks_like_navigation_page(plain_text, summary) and not has_hard_title:
        return False, "导航页特征过强"

    if not categories and policy_signals < 4 and not has_hard_title:
        return False, "政策信号不足"

    if categories == [GENERIC_POLICY_CATEGORY] and not has_hard_title and policy_signals < 4:
        return False, "泛条款信号不足"

    if not meaningful_category and not has_hard_title and insurance_hits < 2 and policy_signals < 5:
        return False, "政策信号不足"

    return True, ""


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
    return parse_policy_text(source, url, plain_text, title)


def parse_policy_pdf(
    source: SourceConfig,
    url: str,
    pdf_text: str,
) -> tuple[PolicyRecord | None, FilteredPageRecord | None]:
    """把 PDF 文本转换为政策记录。"""

    title = _extract_pdf_title(url, source.company)
    return parse_policy_text(source, url, pdf_text, title)


def parse_policy_text(
    source: SourceConfig,
    url: str,
    plain_text: str,
    title: str,
) -> tuple[PolicyRecord | None, FilteredPageRecord | None]:
    """把已经抽出的正文文本转换为政策记录。

    HTML 和 PDF 最终都会复用这套规则，保证过滤口径一致。
    """

    summary = _build_summary(plain_text)
    policy_categories = _guess_categories(plain_text, source.allowed_topics)
    policy_signals = _count_policy_signals(plain_text, title)
    is_policy_like, filter_reason = _looks_like_policy_content(
        url=url,
        title=title,
        summary=summary,
        plain_text=plain_text,
        categories=policy_categories,
        policy_signals=policy_signals,
    )
    if not is_policy_like:
        return None, _build_filtered_record(source, url, title, filter_reason, summary)

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
