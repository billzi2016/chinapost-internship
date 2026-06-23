#!/usr/bin/env python3
"""把训练和评估指标绘制成 JPG。

绘图约定：
- 输出 JPG，不输出 PNG。
- 不显式设置 dpi，使用 Matplotlib 默认 DPI，保留原始导出设置。
- 能画的都画：任务样本数、JSON 通过率、安全风险率、话术污染率、输出长度、训练监控曲线。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def project_dir() -> Path:
    """定位工程根目录。"""
    script = Path(__file__).resolve()
    for parent in script.parents:
        if parent.name == "mlx_qwen_sft":
            return parent
    raise RuntimeError("无法从脚本位置定位 mlx_qwen_sft 目录。")


def parse_args() -> argparse.Namespace:
    """解析绘图参数。"""
    root = project_dir()
    parser = argparse.ArgumentParser(description="Plot evaluation metrics to JPG files.")
    parser.add_argument("--eval-output-dir", type=Path, default=root / "eval_outputs", help="评估指标目录。")
    parser.add_argument("--logs-dir", type=Path, default=root / "logs", help="训练监控日志目录。")
    parser.add_argument("--out-dir", type=Path, default=root / "plots", help="JPG 输出目录。")
    return parser.parse_args()


def read_metrics(eval_output_dir: Path) -> list[dict[str, Any]]:
    """读取所有 *_metrics.json。"""
    records: list[dict[str, Any]] = []
    for path in sorted(eval_output_dir.glob("*_metrics.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        item["label"] = path.name.removesuffix("_metrics.json")
        records.append(item)
    return records


def save_bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path) -> None:
    """保存柱状图为 JPG。"""
    if not labels:
        return
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.2), 4.8))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(path, format="jpg")
    plt.close(fig)


def plot_metric(records: list[dict[str, Any]], task: str, metric: str, out_dir: Path) -> None:
    """对指定 task/metric 跨模型绘图。"""
    labels: list[str] = []
    values: list[float] = []
    for record in records:
        task_metrics = record.get("tasks", {}).get(task, {})
        if metric in task_metrics:
            labels.append(record["label"])
            values.append(float(task_metrics[metric]))
    save_bar(labels, values, f"{task} - {metric}", metric, out_dir / f"{task}_{metric}.jpg")


def read_monitor(logs_dir: Path) -> list[dict[str, Any]]:
    """读取分段训练监控日志。"""
    rows: list[dict[str, Any]] = []
    for path in sorted(logs_dir.glob("train_monitor_*.jsonl")):
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    item = json.loads(line)
                    item["source"] = path.name
                    rows.append(item)
    return rows


def plot_monitor(rows: list[dict[str, Any]], out_dir: Path) -> None:
    """绘制训练过程中可用的自动评估曲线。"""
    if not rows:
        return
    steps = [row["step"] for row in rows]
    safety = [
        row.get("metrics", {}).get("tasks", {}).get("safety", {}).get("risk_rate", 0.0)
        for row in rows
    ]
    fmt = [
        row.get("metrics", {}).get("tasks", {}).get("format", {}).get("json_valid_rate", 0.0)
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(steps, safety, marker="o", label="safety risk rate")
    ax.plot(steps, fmt, marker="o", label="format json valid rate")
    ax.set_xlabel("training step")
    ax.set_ylabel("rate")
    ax.set_title("training collapse monitor")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "training_collapse_monitor.jpg", format="jpg")
    plt.close(fig)


def main() -> None:
    """脚本入口：读取指标并输出多张 JPG。"""
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    records = read_metrics(args.eval_output_dir)
    if records:
        save_bar(
            [record["label"] for record in records],
            [float(record.get("total", 0)) for record in records],
            "evaluated sample count",
            "count",
            args.out_dir / "evaluated_sample_count.jpg",
        )
        for task in ["format", "safety", "postal", "math", "summary", "extract", "rewrite", "code", "logic"]:
            for metric in [
                "avg_output_chars",
                "avg_postal_term_hits",
                "avg_next_step_hits",
                "risk_rate",
                "json_valid_rate",
                "json_required_keys_rate",
                "postal_pollution_rate",
            ]:
                plot_metric(records, task, metric, args.out_dir)

    plot_monitor(read_monitor(args.logs_dir), args.out_dir)
    print(f"plots written to {args.out_dir}")


if __name__ == "__main__":
    main()
