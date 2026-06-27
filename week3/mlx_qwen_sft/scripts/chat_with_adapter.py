#!/usr/bin/env python3
"""本地多轮聊天脚本，支持 base 模型或 LoRA adapter。

设计目标：
- 维护 messages 历史，支持连续对话。
- 优先使用 tokenizer.apply_chat_template，尽量贴近 Qwen2.5-Instruct 的对话格式。
- 如果本地环境没有可用 tokenizer，则退回到简单 role prompt，保证脚本仍可运行。
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_SYSTEM_PROMPT = (
    "你是一个专业、准确、克制的邮政客服助手。"
    "你可以帮助用户理解 EMS、中国邮政、包裹寄递、网点咨询、物流异常、禁限寄、时效和资费等问题。"
    "遇到需要实时查询、政策确认或个人信息核验的问题时，应建议用户通过官方渠道、运单号、网点或人工客服核实。"
    "不要编造赔付金额、具体时限、网点营业时间或官方承诺。"
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Chat with a local MLX base model or LoRA adapter.")
    parser.add_argument("--model", required=True, help="Hugging Face 模型名或本地模型目录。")
    parser.add_argument("--adapter-path", default="", help="LoRA adapter 目录；只聊 base 模型时留空。")
    parser.add_argument("--system", default=DEFAULT_SYSTEM_PROMPT, help="system prompt。")
    parser.add_argument("--max-tokens", type=int, default=512, help="每轮最大生成 token 数。")
    return parser.parse_args()


def load_tokenizer(model: str) -> Any | None:
    """尝试加载 Hugging Face tokenizer。"""
    try:
        from transformers import AutoTokenizer
    except ImportError:
        return None

    try:
        return AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    except Exception:
        return None


def render_prompt(messages: list[dict[str, str]], tokenizer: Any | None) -> str:
    """把 messages 渲染成 prompt。"""
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            pass

    parts: list[str] = []
    for message in messages:
        role = message["role"].upper()
        content = message["content"].strip()
        parts.append(f"{role}: {content}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def clean_generation_text(text: str) -> str:
    """清理 mlx_lm.generate 输出。"""
    cleaned = text.strip()
    if "==========" in cleaned:
        parts = [part.strip() for part in cleaned.split("==========")]
        if len(parts) >= 2 and parts[1]:
            cleaned = parts[1]
    for prefix in ("Prompt: ", "Generation: ", "Peak memory: "):
        lines = [line for line in cleaned.splitlines() if not line.startswith(prefix)]
        cleaned = "\n".join(lines).strip()
    return cleaned.strip()


def run_generate(model: str, adapter_path: str, prompt: str, max_tokens: int) -> str:
    """调用 mlx_lm.generate。"""
    command = [
        "mlx_lm.generate",
        "--model",
        model,
        "--max-tokens",
        str(max_tokens),
        "--prompt",
        prompt,
    ]
    if adapter_path:
        command.extend(["--adapter-path", adapter_path])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "mlx_lm.generate failed")
    return clean_generation_text(result.stdout)


def chat_loop(args: argparse.Namespace) -> None:
    """执行交互式多轮聊天。"""
    tokenizer = load_tokenizer(args.model)
    messages: list[dict[str, str]] = [{"role": "system", "content": args.system}]

    print("输入 /exit 退出，输入 /reset 清空历史重新开始。", flush=True)
    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text == "/exit":
            break
        if user_text == "/reset":
            messages = [{"role": "system", "content": args.system}]
            print("history cleared", flush=True)
            continue

        messages.append({"role": "user", "content": user_text})
        prompt = render_prompt(messages, tokenizer)
        reply = run_generate(args.model, args.adapter_path, prompt, args.max_tokens)
        print(f"assistant> {reply}", flush=True)
        messages.append({"role": "assistant", "content": reply})


def main() -> None:
    """脚本入口。"""
    args = parse_args()
    chat_loop(args)


if __name__ == "__main__":
    main()
