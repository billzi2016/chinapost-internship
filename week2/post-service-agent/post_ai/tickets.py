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
        return TicketPayload.model_validate(payload)
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
    return TicketPayload(
        user_id=user_id,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        service_type=service_type,
        issue_type=issue_type,
        user_request=user_request,
        summary=summary,
        resolution=resolution,
        need_follow_up=need_follow_up,
    )


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
