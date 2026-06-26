"""解析邮寄保险、保价和声明价值相关信息。

本模块只做规则化文本识别，不负责抓取页面。
之所以单独拆出，是因为保险相关字段后续很可能需要独立演进，
例如增加更多国际术语、赔付模板和站点定制解析。
"""

from __future__ import annotations

import re


INSURANCE_CONTEXT_KEYWORDS = [
    "保价",
    "声明价值",
    "insured",
    "insurance coverage",
    "shipment insurance",
    "赔偿",
    "赔付",
    "理赔",
    "索赔",
    "免责",
    "损失",
    "丢失",
    "破损",
]


def _extract_first_match(text: str, patterns: list[str]) -> str:
    """按顺序匹配多个正则，返回第一条命中的文本。"""

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


def parse_insurance_terms(text: str) -> dict[str, object]:
    """从文本中抽取保险与赔付的基础信息。

    参数:
    - text: 清洗后的正文文本。

    返回:
    - 包含保险存在性、类型、赔付上限、索赔期限和免责项的字典。
    """

    lowered = text.lower()
    insurance_context_hits = sum(
        1
        for keyword in INSURANCE_CONTEXT_KEYWORDS
        if keyword.lower() in lowered
    )
    liability_in_context = "liability" in lowered and any(
        token in lowered
        for token in ["loss", "damage", "claim", "compensation", "赔偿", "理赔", "索赔"]
    )
    generic_insurance_in_context = "保险" in text and any(
        token in text
        for token in ["赔偿", "赔付", "理赔", "索赔", "声明价值", "保价", "丢失", "破损"]
    )
    insurance_available = (
        insurance_context_hits >= 2
        or "保价" in text
        or "声明价值" in text
        or "declared value" in lowered
        or "shipment insurance" in lowered
        or liability_in_context
        or generic_insurance_in_context
    )

    insurance_type = "未知"
    if not insurance_available:
        insurance_type = "未知"
    elif "声明价值" in text or "declared value" in lowered:
        insurance_type = "声明价值"
    elif "保价" in text:
        insurance_type = "保价"
    elif generic_insurance_in_context or "shipment insurance" in lowered:
        insurance_type = "运输保险"
    elif liability_in_context:
        insurance_type = "承运商责任"

    compensation_limit = _extract_first_match(
        text,
        [
            r"最高赔偿[^。；;\n]*",
            r"赔偿上限[^。；;\n]*",
            r"责任限额[^。；;\n]*",
            r"up to [^.;\n]*",
        ],
    )
    claim_deadline = _extract_first_match(
        text,
        [
            r"\d+\s*日内[^。；;\n]*提出[^。；;\n]*",
            r"\d+\s*天内[^。；;\n]*索赔[^。；;\n]*",
            r"claim[^.;\n]*within[^.;\n]*",
        ],
    )

    exclusions: list[str] = []
    exclusion_map = {
        "现金": ["现金", "currency"],
        "珠宝": ["珠宝", "jewelry"],
        "易碎品": ["易碎", "fragile"],
        "活体": ["活体", "live animals"],
        "危险品": ["危险品", "dangerous goods"],
        "生鲜": ["生鲜", "perishable"],
    }
    for label, keywords in exclusion_map.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            exclusions.append(label)

    requirements: list[str] = []
    requirement_map = {
        "价值证明": ["发票", "价值证明", "invoice"],
        "破损照片": ["照片", "破损图", "damage photo"],
        "签收证明": ["签收证明", "proof of delivery"],
        "温控记录": ["温控记录", "temperature record"],
    }
    for label, keywords in requirement_map.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            requirements.append(label)

    return {
        "insurance_available": insurance_available,
        "insurance_type": insurance_type,
        "compensation_limit": compensation_limit,
        "claim_deadline": claim_deadline,
        "insurance_exclusions": exclusions,
        "requirements": requirements,
    }
