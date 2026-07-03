#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual streaming chat client for the local MLX service.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18731")
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=512)
    return parser.parse_args()


def request_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_model(base_url: str, explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model
    payload = request_json(f"{base_url.rstrip('/')}/v1/models")
    return str(payload["data"][0]["id"])


def print_service_info(base_url: str) -> None:
    payload = request_json(f"{base_url.rstrip('/')}/")
    print(f"service_config: {payload.get('config_path')}")
    print(f"service_adapter: {payload.get('adapter_path')}")


def stream_chat(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "stream": True,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    chunks: list[str] = []
    with urllib.request.urlopen(request, timeout=None) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            data = line.removeprefix("data: ").strip()
            if data == "[DONE]":
                break
            event = json.loads(data)
            delta = event["choices"][0].get("delta", {})
            piece = delta.get("content")
            if not piece:
                continue
            print(piece, end="", flush=True)
            chunks.append(piece)
    print()
    return "".join(chunks).strip()


def main() -> int:
    args = parse_args()
    messages: list[dict[str, str]] = []

    try:
        print_service_info(args.base_url)
        model = resolve_model(args.base_url, args.model)
    except (KeyError, urllib.error.URLError, TimeoutError) as exc:
        print(f"无法连接本地服务或读取模型列表: {exc}", file=sys.stderr)
        return 1

    print(f"model: {model}")
    print("输入问题开始多轮对话；输入 /reset 清空上下文；输入 /exit 或 /quit 退出。")

    while True:
        try:
            user_text = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not user_text:
            continue
        if user_text in {"/exit", "/quit"}:
            return 0
        if user_text == "/reset":
            messages.clear()
            print("上下文已清空。")
            continue

        messages.append({"role": "user", "content": user_text})
        print("助手: ", end="", flush=True)
        try:
            assistant_text = stream_chat(
                args.base_url,
                model,
                messages,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        except urllib.error.HTTPError as exc:
            print(f"\n请求失败: HTTP {exc.code} {exc.read().decode('utf-8', errors='ignore')}", file=sys.stderr)
            messages.pop()
            continue
        except urllib.error.URLError as exc:
            print(f"\n请求失败: {exc}", file=sys.stderr)
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": assistant_text})


if __name__ == "__main__":
    raise SystemExit(main())
