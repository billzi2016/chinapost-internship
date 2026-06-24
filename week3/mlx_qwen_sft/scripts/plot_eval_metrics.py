#!/usr/bin/env python3
"""训练过程评估指标绘图。

设计目标：
- 训练过程中可反复调用，每次覆盖保存同名 JPG。
- 图上只保留短标题、坐标轴和图例，不放大段说明。
- 不显式设置 dpi，沿用 Matplotlib 默认导出 DPI。
- 同时支持单次训练 run 和全量历史指标。
"""

from __future__ import annotations

import argparse
import json
import re
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
    parser = argparse.ArgumentParser(description="Plot training/evaluation metrics to JPG files.")
    parser.add_argument("--eval-output-dir", type=Path, default=root / "eval_outputs", help="评估指标目录。")
    parser.add_argument("--logs-dir", type=Path, default=root / "logs", help="训练监控日志目录。")
    parser.add_argument("--out-dir", type=Path, default=root / "plots", help="JPG 输出目录。")
    parser.add_argument("--monitor", type=Path, default=None, help="只绘制指定 train_monitor JSONL。")
    parser.add_argument("--label", default="", help="输出文件名前缀；训练中建议传入模型 label。")
    return parser.parse_args()


def safe_name(value: str) -> str:
    """把 label 转成适合作为文件名的短前缀。"""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def output_path(out_dir: Path, label: str, name: str) -> Path:
    """生成固定 JPG 输出路径，重复绘图会覆盖同名文件。"""
    prefix = safe_name(label)
    filename = f"{prefix}_{name}.jpg" if prefix else f"{name}.jpg"
    return out_dir / filename


def read_monitor_files(logs_dir: Path, monitor: Path | None) -> list[dict[str, Any]]:
    """读取训练监控 JSONL。"""
    paths = [monitor] if monitor else sorted(logs_dir.glob("train_monitor_*.jsonl"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path or not path.exists():
            continue
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                row = json.loads(line)
                row["source"] = path.name
                rows.append(row)
    return rows


def read_metrics(eval_output_dir: Path) -> list[dict[str, Any]]:
    """读取所有评估汇总 JSON。"""
    records: list[dict[str, Any]] = []
    for path in sorted(eval_output_dir.glob("*_metrics.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        item["label"] = path.name.removesuffix("_metrics.json")
        records.append(item)
    return records


def metric(row: dict[str, Any], task: str, key: str, default: float = 0.0) -> float:
    """从 monitor row 里取某个 task 指标。"""
    value = row.get("metrics", {}).get("tasks", {}).get(task, {}).get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def save_line(
    rows: list[dict[str, Any]],
    series: list[tuple[str, list[float]]],
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    """保存折线图。"""
    if not rows:
        return
    steps = [int(row.get("step", index + 1)) for index, row in enumerate(rows)]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for name, values in series:
        ax.plot(steps, values, marker="o", linewidth=1.8, label=name)
    ax.set_title(title)
    ax.set_xlabel("step")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, format="jpg")
    plt.close(fig)


def save_bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path) -> None:
    """保存柱状图。"""
    if not labels:
        return
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.0), 4.8))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=35)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, format="jpg")
    plt.close(fig)


def plot_series(ax: Any, steps: list[int], series: list[tuple[str, list[float]]], title: str, ylabel: str) -> None:
    """在已有子图上画折线。"""
    for name, values in series:
        ax.plot(steps, values, marker="o", linewidth=1.6, label=name)
    ax.set_title(title)
    ax.set_xlabel("step")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)


def plot_monitor(rows: list[dict[str, Any]], out_dir: Path, label: str) -> None:
    """绘制 2x2 训练监控组图。"""
    if not rows:
        return
    rows = sorted(rows, key=lambda row: int(row.get("step", 0)))
    steps = [int(row.get("step", index + 1)) for index, row in enumerate(rows)]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    plot_series(
        axes[0][0],
        steps,
        [("score", [float(row.get("score", 0.0)) for row in rows])],
        "Eval score",
        "score",
    )
    plot_series(
        axes[0][1],
        steps,
        [
            ("json valid", [metric(row, "format", "json_valid_rate") for row in rows]),
            ("json keys", [metric(row, "format", "json_required_keys_rate") for row in rows]),
        ],
        "JSON format",
        "rate",
    )
    plot_series(
        axes[1][0],
        steps,
        [
            ("safety risk", [metric(row, "safety", "risk_rate") for row in rows]),
            ("pollution max", [max_pollution(row) for row in rows]),
        ],
        "Risk guard",
        "rate",
    )
    plot_series(
        axes[1][1],
        steps,
        [
            ("postal terms", [metric(row, "postal", "avg_postal_term_hits") for row in rows]),
            ("next steps", [metric(row, "postal", "avg_next_step_hits") for row in rows]),
        ],
        "Postal signal",
        "avg hits",
    )
    fig.tight_layout()
    fig.savefig(output_path(out_dir, label, "training_dashboard"), format="jpg")
    plt.close(fig)


def max_pollution(row: dict[str, Any]) -> float:
    """取当前 step 所有通用任务中最大的污染率。"""
    values = [
        float(task_metrics.get("postal_pollution_rate", 0.0))
        for task_metrics in row.get("metrics", {}).get("tasks", {}).values()
        if "postal_pollution_rate" in task_metrics
    ]
    return max(values) if values else 0.0


def plot_latest_task_bars(records: list[dict[str, Any]], out_dir: Path, label: str) -> None:
    """绘制最新一次评估的任务输出长度。"""
    if not records:
        return
    latest = records[-1]
    tasks = latest.get("tasks", {})
    task_names = sorted(tasks)
    save_bar(
        task_names,
        [float(tasks[name].get("avg_output_chars", 0.0)) for name in task_names],
        "output length",
        "chars",
        output_path(out_dir, label, "latest_output_length"),
    )


def main() -> None:
    """脚本入口：读取训练/评估指标并覆盖保存 JPG。"""
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = read_monitor_files(args.logs_dir, args.monitor)
    records = read_metrics(args.eval_output_dir)
    plot_monitor(rows, args.out_dir, args.label)
    plot_latest_task_bars(records, args.out_dir, args.label)
    print(f"plots written to {args.out_dir}")


if __name__ == "__main__":
    main()
