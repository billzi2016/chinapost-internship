#!/usr/bin/env python3
"""把 raw JSON 转换成 mlx-lm 可直接训练的 chat JSONL。

输入：
- data/raw/train.json
- data/raw/val.json
- data/raw/test.json
- data/raw/who_am_i.json

输出：
- data/train.jsonl
- data/valid.jsonl
- data/test.jsonl

转换原则：
- 保留原始 raw 文件，不在脚本里修改原始数据。
- 每个 QA 摘要转成一条 SFT 样本，避免超长整段对话撑爆上下文。
- who_am_i.json 作为少量身份设定样本加入训练集，提高邮政客服角色稳定性。
- 每行一个 JSON 对象，符合 mlx-lm 的 chat 数据格式。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - 兼容没有安装 tqdm 的干净环境。
    def tqdm(iterable, **_: Any):  # type: ignore[no-redef]
        """没有 tqdm 时退化为普通迭代，保证脚本仍可运行。"""
        return iterable


SYSTEM_PROMPT = (
    "你是一个专业、准确、克制的邮政客服助手。"
    "你可以帮助用户理解 EMS、中国邮政、包裹寄递、网点咨询、物流异常、禁限寄、时效和资费等问题。"
    "遇到需要实时查询、政策确认或个人信息核验的问题时，应建议用户通过官方渠道、运单号、网点或人工客服核实。"
    "不要编造赔付金额、具体时限、网点营业时间或官方承诺。"
)


def project_dir() -> Path:
    """定位 mlx_qwen_sft 工程根目录，避免依赖用户机器绝对路径。"""
    script = Path(__file__).resolve()
    for parent in script.parents:
        if parent.name == "mlx_qwen_sft":
            return parent
    raise RuntimeError("无法从脚本位置定位 mlx_qwen_sft 目录。")


def parse_args() -> argparse.Namespace:
    """解析数据转换参数。"""
    root = project_dir()
    parser = argparse.ArgumentParser(description="Prepare MLX chat JSONL data from raw SFT JSON.")
    parser.add_argument("--raw-dir", type=Path, default=root / "data" / "raw", help="原始 JSON 目录。")
    parser.add_argument("--out-dir", type=Path, default=root / "data", help="输出 JSONL 目录。")
    parser.add_argument("--max-train", type=int, default=0, help="最多写入多少条训练样本，0 表示不限制。")
    parser.add_argument("--max-valid", type=int, default=0, help="最多写入多少条验证样本，0 表示不限制。")
    parser.add_argument("--max-test", type=int, default=0, help="最多写入多少条测试样本，0 表示不限制。")
    return parser.parse_args()


def read_json(path: Path) -> list[dict[str, Any]]:
    """读取列表形式 JSON，并对格式做显式检查。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} 不是 JSON list。")
    return data


def normalize_text(value: Any) -> str:
    """把字段统一清洗成单行文本，避免 JSONL 中出现不可控空白。"""
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    text = str(value).replace("\r", " ").replace("\n", " ")
    return " ".join(text.split()).strip()


def qa_examples(record: dict[str, Any]) -> list[dict[str, Any]]:
    """从一条原始会话中抽取多条 QA 训练样本。"""
    examples: list[dict[str, Any]] = []
    dialogue_id = record.get("DialogueID")
    for index, qa in enumerate(record.get("QA") or []):
        question = normalize_text(qa.get("QueSumm") or qa.get("QASumm"))
        answer = normalize_text(
            qa.get("AnsSummLong")
            or qa.get("AnsSummShort")
            or qa.get("QASumm")
            or "建议通过官方渠道进一步核实。"
        )
        intent = normalize_text(qa.get("intent"))
        if not question or not answer:
            continue
        if intent:
            question = f"{question}\n\n用户意图：{intent}"
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
                "meta": {"dialogue_id": dialogue_id, "qa_index": index, "source": "qa_summary"},
            }
        )
    return examples


def identity_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """兼容 who_am_i.json 的常见字段，把身份问答加入训练集。"""
    examples: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if "messages" in record:
            messages = record["messages"]
            if isinstance(messages, list) and messages:
                examples.append({"messages": messages, "meta": {"source": "who_am_i", "index": index}})
            continue
        question = normalize_text(record.get("question") or record.get("prompt") or record.get("user"))
        answer = normalize_text(record.get("answer") or record.get("response") or record.get("assistant"))
        if question and answer:
            examples.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "meta": {"source": "who_am_i", "index": index},
                }
            )
    return examples


def convert_split(raw_path: Path, limit: int) -> list[dict[str, Any]]:
    """转换 train/val/test 单个 split。"""
    output: list[dict[str, Any]] = []
    for record in tqdm(read_json(raw_path), desc=f"convert {raw_path.name}"):
        output.extend(qa_examples(record))
        if limit and len(output) >= limit:
            return output[:limit]
    return output


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """写出单行 JSONL，供 mlx-lm 直接读取。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    """脚本入口：转换三个 split，并输出转换统计。"""
    args = parse_args()
    raw_dir = args.raw_dir.resolve()
    out_dir = args.out_dir.resolve()

    train = convert_split(raw_dir / "train.json", args.max_train)
    valid = convert_split(raw_dir / "val.json", args.max_valid)
    test = convert_split(raw_dir / "test.json", args.max_test)

    who_am_i_path = raw_dir / "who_am_i.json"
    if who_am_i_path.exists():
        train.extend(identity_examples(read_json(who_am_i_path)))

    write_jsonl(out_dir / "train.jsonl", train)
    write_jsonl(out_dir / "valid.jsonl", valid)
    write_jsonl(out_dir / "test.jsonl", test)

    summary = {"train": len(train), "valid": len(valid), "test": len(test)}
    (out_dir / "prepare_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
