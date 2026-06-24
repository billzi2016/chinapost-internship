#!/usr/bin/env python3
"""绘制 rank sweep 横向对比图。

输入是 runs/<run-id>/rank_<rank>/ 结构。图上只保留短标题、
坐标轴和图例，详细解释写到报告里。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def project_dir() -> Path:
    """定位 mlx_qwen_sft 工程根目录。"""
    script = Path(__file__).resolve()
    for parent in script.parents:
        if parent.name == "mlx_qwen_sft":
            return parent
    raise RuntimeError("无法从脚本位置定位 mlx_qwen_sft 目录。")


def parse_args() -> argparse.Namespace:
    """解析绘图参数。"""
    root = project_dir()
    parser = argparse.ArgumentParser(description="Plot rank sweep comparison.")
    parser.add_argument("--run-dir", type=Path, required=True, help="rank sweep 实验目录。")
    parser.add_argument("--out-dir", type=Path, default=None, help="输出目录，默认 run-dir/plots。")
    parser.add_argument("--name", default="rank_comparison", help="输出文件名，不含扩展名。")
    parser.add_argument("--title", default="3B rank sweep", help="组图短标题。")
    parser.set_defaults(out_dir=None)
    return parser.parse_args()


def rank_from_dir(path: Path) -> int:
    """从 rank_<n> 目录名中取 rank。"""
    match = re.search(r"rank_(\d+)$", path.name)
    if not match:
        raise ValueError(f"无法识别 rank 目录：{path}")
    return int(match.group(1))


def read_json(path: Path) -> dict[str, Any]:
    """读取 JSON 文件。"""
    return json.loads(path.read_text(encoding="utf-8"))


def read_best(rank_dir: Path) -> dict[str, Any]:
    """读取某个 rank 的 best metadata。"""
    files = sorted((rank_dir / "logs").glob("best_adapter_*.json"))
    if not files:
        files = sorted((rank_dir / "best_adapter").glob("best_adapter_*.json"))
    if not files:
        raise FileNotFoundError(f"缺少 best metadata：{rank_dir}")
    return read_json(files[-1])


def read_final_monitor(rank_dir: Path) -> dict[str, Any]:
    """读取某个 rank 最后一条 monitor 记录。"""
    files = sorted((rank_dir / "logs").glob("train_monitor_*.jsonl"))
    if not files:
        raise FileNotFoundError(f"缺少 train monitor：{rank_dir}")
    rows = [json.loads(line) for line in files[-1].read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[-1]


def task_metric(metrics: dict[str, Any], task: str, key: str, default: float = 0.0) -> float:
    """安全读取 task 指标。"""
    value = metrics.get("tasks", {}).get(task, {}).get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def collect_rows(run_dir: Path) -> list[dict[str, Any]]:
    """汇总每个 rank 的 best 和 final 指标。"""
    rows: list[dict[str, Any]] = []
    for rank_dir in sorted(run_dir.glob("rank_*"), key=rank_from_dir):
        rank = rank_from_dir(rank_dir)
        best = read_best(rank_dir)
        final = read_final_monitor(rank_dir)
        best_metrics = best["metrics"]
        final_metrics = final["metrics"]
        rows.append(
            {
                "rank": rank,
                "best_step": int(best["best_step"]),
                "best_score": float(best["best_score"]),
                "final_score": float(final["score"]),
                "json_keys": task_metric(best_metrics, "format", "json_required_keys_rate"),
                "json_valid": task_metric(best_metrics, "format", "json_valid_rate"),
                "safety": task_metric(best_metrics, "safety", "risk_rate"),
                "postal_terms": task_metric(best_metrics, "postal", "avg_postal_term_hits"),
                "next_steps": task_metric(best_metrics, "postal", "avg_next_step_hits"),
                "final_json_keys": task_metric(final_metrics, "format", "json_required_keys_rate"),
                "final_safety": task_metric(final_metrics, "safety", "risk_rate"),
            }
        )
    return rows


def plot_line(ax: Any, ranks: list[int], series: list[tuple[str, list[float]]], title: str, ylabel: str) -> None:
    """画一个子图。"""
    for label, values in series:
        ax.plot(ranks, values, marker="o", linewidth=1.6, label=label)
    ax.set_title(title)
    ax.set_xlabel("rank")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)


def save_plot(rows: list[dict[str, Any]], out_path: Path, title: str) -> None:
    """保存 2x2 rank 对比组图。"""
    ranks = [row["rank"] for row in rows]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    fig.suptitle(title, fontsize=12)
    plot_line(
        axes[0][0],
        ranks,
        [
            ("best", [row["best_score"] for row in rows]),
            ("final", [row["final_score"] for row in rows]),
        ],
        "Score",
        "score",
    )
    plot_line(
        axes[0][1],
        ranks,
        [
            ("json valid", [row["json_valid"] for row in rows]),
            ("json keys", [row["json_keys"] for row in rows]),
        ],
        "JSON",
        "rate",
    )
    plot_line(
        axes[1][0],
        ranks,
        [
            ("risk", [row["safety"] for row in rows]),
        ],
        "Safety",
        "rate",
    )
    plot_line(
        axes[1][1],
        ranks,
        [
            ("terms", [row["postal_terms"] for row in rows]),
            ("steps", [row["next_steps"] for row in rows]),
        ],
        "Postal",
        "avg hits",
    )
    fig.tight_layout()
    fig.savefig(out_path, format="jpg")
    plt.close(fig)


def main() -> None:
    """脚本入口。"""
    args = parse_args()
    run_dir = args.run_dir.resolve()
    out_dir = args.out_dir.resolve() if args.out_dir else run_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_rows(run_dir)
    json_path = run_dir / f"{args.name}.json"
    jpg_path = out_dir / f"{args.name}.jpg"
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_plot(rows, jpg_path, args.title)
    print(f"rank comparison jpg written to {jpg_path}")
    print(f"rank comparison json written to {json_path}")


if __name__ == "__main__":
    main()
