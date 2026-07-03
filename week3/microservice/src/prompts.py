from __future__ import annotations

from typing import Any

from src.schemas import AppConfig, ChatCompletionRequest


def build_system_prompt(config: AppConfig) -> str:
    prompt = config.model.system_prompt.strip()
    extras = [
        "你的当前角色是中国邮政/EMS 场景下的本地客服助手。"
        "当用户询问你是谁、你的角色、你的身份、who are you 或类似问题时，"
        "优先说明你是邮政客服助手，可以协助处理寄递、物流、网点、禁限寄、时效、资费和售后相关问题。"
    ]

    if config.model.knowledge_cutoff_date:
        extras.append(
            f"知识库可用信息的时间边界截至 {config.model.knowledge_cutoff_date}。"
            "凡是明显依赖当前时间、当前日期、当前天气、当前物流状态、当前网点状态"
            "或该日期之后可能变化的信息，不要把知识库内容当作最新事实直接回答。"
        )

    extras.append(
        "如果有工具结果，优先依据工具结果回答；如果没有实时结果，"
        "应明确说明需要进一步查询或通过官方渠道、运单号、网点或人工客服核实。"
    )
    return " ".join([prompt, *extras])


def build_messages(config: AppConfig, request: ChatCompletionRequest) -> list[dict[str, str]]:
    messages = [message.model_dump() for message in request.messages]
    if not any(message["role"] == "system" for message in messages):
        messages.insert(0, {"role": "system", "content": build_system_prompt(config)})
    return messages


def load_tokenizer(model_path: str) -> Any | None:
    try:
        from transformers import AutoTokenizer
    except ImportError:
        return None

    try:
        return AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    except Exception:
        return None


def render_prompt(messages: list[dict[str, str]], tokenizer: Any | None) -> str:
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            pass

    parts = [f"{message['role'].upper()}: {message['content'].strip()}" for message in messages]
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def clean_generation_text(text: str) -> str:
    cleaned = text.strip()
    if "==========" in cleaned:
        parts = [part.strip() for part in cleaned.split("==========")]
        if len(parts) >= 2 and parts[1]:
            cleaned = parts[1]
    for prefix in ("Prompt: ", "Generation: ", "Peak memory: "):
        lines = [line for line in cleaned.splitlines() if not line.startswith(prefix)]
        cleaned = "\n".join(lines).strip()
    return cleaned.strip()
