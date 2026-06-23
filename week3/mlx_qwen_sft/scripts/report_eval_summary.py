#!/usr/bin/env python3
"""把评估指标汇总成 Markdown，便于写周报和报告。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def project_dir() -> Path:
    """定位工程根目录。"""
    script = Path(__file__).resolve()
    for parent in script.parents:
        if parent.name == "mlx_qwen_sft":
            return parent
    raise RuntimeError("无法从脚本位置定位 mlx_qwen_sft 目录。")


def parse_args() -> argparse.Namespace:
    """解析输入输出目录。"""
    root = project_dir()
    parser = argparse.ArgumentParser(description="Build a Markdown evaluation summary.")
    parser.add_argument("--eval-output-dir", type=Path, default=root / "eval_outputs", help="评估指标目录。")
    parser.add_argument("--out", type=Path, default=root / "eval_summary.md", help="汇总 Markdown 路径。")
    return parser.parse_args()


def load_metrics(directory: Path) -> list[dict[str, Any]]:
    """读取所有评估指标 JSON。"""
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*_metrics.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["label"] = path.name.removesuffix("_metrics.json")
        records.append(record)
    return records


def fmt(value: Any) -> str:
    """把指标值格式化成表格文本。"""
    if isinstance(value, float):
        return f"{value:.3f}"
    if value is None:
        return "-"
    return str(value)


def main() -> None:
    """脚本入口：生成 Markdown 表格。"""
    args = parse_args()
    records = load_metrics(args.eval_output_dir)

    lines = ["# 模型评估汇总", ""]
    if not records:
        lines.append("暂无评估指标。先运行 `scripts/evaluate_model.py`。")
    for record in records:
        lines.extend([f"## {record['label']}", "", "| task | count | avg chars | json valid | safety risk | postal pollution |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for task, metrics in sorted(record.get("tasks", {}).items()):
            lines.append(
                "| "
                + " | ".join(
                    [
                        task,
                        fmt(metrics.get("count")),
                        fmt(metrics.get("avg_output_chars")),
                        fmt(metrics.get("json_valid_rate")),
                        fmt(metrics.get("risk_rate")),
                        fmt(metrics.get("postal_pollution_rate")),
                    ]
                )
                + " |"
            )
        lines.append("")

    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"summary written to {args.out}")


if __name__ == "__main__":
    main()
