"""解析 HTML 文本，提取基础政策信息。

当前实现只做通用文本抽取和主题判断，不写站点定制逻辑。
后续如果某个站点结构复杂，应新增专门解析器，而不是把条件堆到本文件中。
"""

from __future__ import annotations

import re
from html import unescape

from crawler.insurance_parser import parse_insurance_terms
from crawler.models import PolicyRecord, SourceConfig


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


def parse_policy_page(source: SourceConfig, url: str, html_text: str) -> PolicyRecord:
    """把 HTML 页面转换为政策记录。"""

    plain_text = _strip_html_tags(html_text)
    summary = plain_text[:300]
    insurance_info = parse_insurance_terms(plain_text)

    return PolicyRecord(
        source_id=source.source_id,
        company=source.company,
        url=url,
        title=source.company,
        policy_categories=_guess_categories(plain_text, source.allowed_topics),
        summary=summary,
        evidence_text=summary,
        insurance_available=insurance_info["insurance_available"],
        insurance_type=insurance_info["insurance_type"],
        compensation_limit=insurance_info["compensation_limit"],
        claim_deadline=insurance_info["claim_deadline"],
        requirements=insurance_info["requirements"],
        insurance_exclusions=insurance_info["insurance_exclusions"],
    )
