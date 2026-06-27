"""解析官方客服知识库 FAQ JSON。"""

from __future__ import annotations

import json
import re
from html import unescape

from crawler.models import FilteredPageRecord, PolicyRecord, SourceConfig
from crawler.parser import parse_policy_text


def parse_faq_json(
    source: SourceConfig,
    url: str,
    json_text: str,
) -> tuple[list[PolicyRecord], list[FilteredPageRecord]]:
    """把客服知识库 JSON 转成政策记录和过滤审计记录。"""

    payload = json.loads(json_text)
    records: list[PolicyRecord] = []
    filtered: list[FilteredPageRecord] = []
    for section in payload.get("data", []):
        section_name = str(section.get("name") or "常见问题")
        for item in section.get("faqList") or []:
            question = _clean_text(str(item.get("question") or ""))
            answer = _clean_text(str(item.get("answer") or ""))
            if _should_skip_faq(question, answer):
                continue
            faq_url = f"{url}#faq-{item.get('id', question)}"
            text = f"栏目：{section_name}。问题：{question}。答案：{answer}"
            record, filtered_record = parse_policy_text(source, faq_url, text, question)
            if record is not None:
                records.append(record)
            elif filtered_record is not None:
                filtered.append(filtered_record)
    return records, filtered


def _clean_text(value: str) -> str:
    """清理 FAQ answer 中的 HTML 标签和实体。"""

    text = unescape(value)
    text = re.sub(r"<br\s*/?>", "。", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _should_skip_faq(question: str, answer: str) -> bool:
    """跳过跳转机器人、空答案和明显无正文的 FAQ。"""

    if not question or not answer:
        return True
    if answer in {"跳转机器人", "暂无数据"}:
        return True
    return len(f"{question}{answer}") < 40
