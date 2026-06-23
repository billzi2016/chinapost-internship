from __future__ import annotations

from post_ai.schemas import ChatMessage, RetrievalHit


SYSTEM_PROMPT = """你是邮政客服智能助手。优先依据引用对话回答用户问题。
不要使用非邮政客服泛化内容。不确定时说明缺少依据。
回答要清楚、克制、面向客服业务。"""


def build_rag_messages(user_query: str, hits: list[RetrievalHit]) -> list[ChatMessage]:
    citations = "\n\n".join(
        f"[引用{hit.rank} score={hit.score:.4f}]\n{hit.document.content}" for hit in hits
    )
    user_content = f"用户问题:\n{user_query}\n\n可用引用对话:\n{citations or '无'}"
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]


def build_title_messages(conversation_text: str) -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="请为对话生成不超过20个汉字的中文标题，不要引号，不要Markdown。"),
        ChatMessage(role="user", content=conversation_text),
    ]


def build_ticket_messages(conversation_text: str) -> list[ChatMessage]:
    return [
        ChatMessage(
            role="system",
            content=(
                "根据对话生成严格合法JSON。字段必须包含 user_id, timestamp, service_type, "
                "issue_type, user_request, summary, resolution, need_follow_up。不要Markdown。"
            ),
        ),
        ChatMessage(role="user", content=conversation_text),
    ]
