from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from post_ai.prompts import build_ticket_messages
from post_ai.providers.base import ModelProvider, ProviderError
from post_ai.schemas import TicketPayload


class TicketJSONError(ValueError):
    pass


def parse_ticket_json(text: str) -> TicketPayload:
    cleaned = _strip_code_fence(text.strip())
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise TicketJSONError(f"Ticket output is not valid JSON: {exc}") from exc
    try:
        return normalize_ticket_payload(TicketPayload.model_validate(payload))
    except ValidationError as exc:
        raise TicketJSONError(f"Ticket JSON schema validation failed: {exc}") from exc


def build_rule_based_ticket(
    user_request: str,
    summary: str,
    resolution: str = "",
    issue_type: str = "",
    service_type: str = "邮政客服",
    user_id: str = "",
    need_follow_up: bool = False,
) -> TicketPayload:
    return normalize_ticket_payload(TicketPayload(
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        service_type=service_type,
        issue_type=issue_type,
        user_request=user_request,
        summary=summary,
        resolution=resolution,
        need_follow_up=need_follow_up,
    ))


def normalize_ticket_payload(ticket: TicketPayload) -> TicketPayload:
    ticket.service_type = _normalize_service_type(ticket.service_type)
    ticket.issue_type = _normalize_issue_type(ticket.issue_type)
    ticket.user_request = _normalize_english_text(ticket.user_request, "用户咨询邮政业务办理。")
    ticket.summary = _normalize_english_text(ticket.summary, "已根据当前对话整理用户诉求和客服处理过程。")
    ticket.resolution = _normalize_english_text(ticket.resolution, "")
    return ticket


def _normalize_service_type(value: str) -> str:
    text = value.strip()
    if not text or _looks_english(text):
        return "邮政客服"
    return text


def _normalize_issue_type(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    lower = text.lower()
    mappings = {
        "shipping": "寄递咨询",
        "large item shipping": "大件寄递咨询",
        "delivery": "配送咨询",
        "tracking": "物流查询",
        "refund": "退款咨询",
    }
    if lower in mappings:
        return mappings[lower]
    if "large" in lower and "shipping" in lower:
        return "大件寄递咨询"
    if _looks_english(text):
        return "邮政业务咨询"
    return text


def _normalize_english_text(value: str, fallback: str) -> str:
    text = value.strip()
    if text and not _looks_english(text):
        return text
    return fallback


def _looks_english(text: str) -> bool:
    letters = sum(1 for char in text if char.isascii() and char.isalpha())
    chinese = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return letters > 0 and chinese == 0


def ticket_to_json(ticket: TicketPayload) -> str:
    return json.dumps(ticket.model_dump(), ensure_ascii=False, indent=2)


def generate_ticket_json_with_provider(
    provider: ModelProvider,
    model: str,
    conversation_text: str,
) -> TicketPayload:
    result = provider.chat(messages=build_ticket_messages(conversation_text), model=model)
    try:
        return parse_ticket_json(result.content)
    except TicketJSONError:
        repair = provider.chat(
            messages=build_ticket_repair_messages(result.content),
            model=model,
        )
        return parse_ticket_json(repair.content)


def build_ticket_repair_messages(raw_output: str):
    from post_ai.schemas import ChatMessage

    return [
        ChatMessage(
            role="system",
            content=(
                "把输入修复为严格合法JSON，只输出JSON。字段必须包含 "
                "user_id, timestamp, service_type, issue_type, user_request, "
                "summary, resolution, need_follow_up。need_follow_up 必须是 boolean。"
                "所有字符串字段必须使用简体中文；service_type 固定写“邮政客服”。"
            ),
        ),
        ChatMessage(role="user", content=raw_output),
    ]


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text
