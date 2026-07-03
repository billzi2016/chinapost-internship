#!/usr/bin/env python3
"""Build global 3B vs 7B comparison from structured monitor data.

This script never reads existing plot images. It only reads
rank_*/logs/train_monitor_*.jsonl and recomputes summary metrics.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "global_compare"
PLOTS_DIR = OUT_DIR / "plots"

RUNS = {
    "3B": ROOT / "runs" / "20260703_021130_qwen2.5-3b-lora_rank_sweep",
    "7B": ROOT / "runs" / "20260703_045302_qwen2.5-7b-lora_rank_sweep",
}


def metric(row: dict[str, Any], task: str, name: str, default: float = 0.0) -> float:
    value = row.get("metrics", {}).get("tasks", {}).get(task, {}).get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_rank_rows(rank_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for monitor in sorted((rank_dir / "logs").glob("train_monitor_*.jsonl")):
        for line in monitor.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if "step" in record and "metrics" in record:
                rows.append(record)
    by_step = {int(row["step"]): row for row in rows}
    return [by_step[step] for step in sorted(by_step)]


def summarize_run(model: str, run_dir: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for rank_dir in sorted(run_dir.glob("rank_*"), key=lambda path: int(path.name.split("_")[1])):
        rows = read_rank_rows(rank_dir)
        if not rows:
            continue
        rank = int(rank_dir.name.split("_")[1])
        best = max(rows, key=lambda row: float(row.get("score", float("-inf"))))
        final = rows[-1]
        label = f"qwen2.5-{model.lower()}-lora-r{rank}"
        summaries.append(
            {
                "model": model,
                "rank": rank,
                "steps": len(rows),
                "last_step": int(final["step"]),
                "best_step": int(best["step"]),
                "best_score": float(best.get("score", 0.0)),
                "final_score": float(final.get("score", 0.0)),
                "score_drop": float(best.get("score", 0.0)) - float(final.get("score", 0.0)),
                "json_valid": metric(best, "format", "json_valid_rate"),
                "json_keys": metric(best, "format", "json_required_keys_rate"),
                "safety_risk": metric(best, "safety", "risk_rate"),
                "postal_terms": metric(best, "postal", "avg_postal_term_hits"),
                "next_steps": metric(best, "postal", "avg_next_step_hits"),
                "ceval_acc": metric(best, "ceval_choice", "choice_accuracy"),
                "adapter": str((rank_dir / "best_adapter" / label).relative_to(ROOT)),
            }
        )
    return summaries


def write_csv(rows: list[dict[str, Any]]) -> None:
    path = OUT_DIR / "global_rank_summary.csv"
    fields = [
        "model",
        "rank",
        "steps",
        "last_step",
        "best_step",
        "best_score",
        "final_score",
        "score_drop",
        "json_valid",
        "json_keys",
        "safety_risk",
        "postal_terms",
        "next_steps",
        "ceval_acc",
        "adapter",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_metric(rows: list[dict[str, Any]], name: str, ylabel: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=160)
    for model in RUNS:
        selected = [row for row in rows if row["model"] == model]
        selected.sort(key=lambda row: row["rank"])
        ax.plot(
            [row["rank"] for row in selected],
            [row[name] for row in selected],
            marker="o",
            linewidth=2,
            label=model,
        )
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16, 32])
    ax.set_xticklabels(["1", "2", "4", "8", "16", "32"])
    ax.set_xlabel("LoRA rank")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / filename)
    plt.close(fig)


def recommended_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Choose deployable rows, not just the highest transient best score."""
    selected: list[dict[str, Any]] = []
    for model in RUNS:
        model_rows = [row for row in rows if row["model"] == model]
        stable = [
            row
            for row in model_rows
            if row["json_keys"] > 0.0 and row["score_drop"] <= 0.5 and row["safety_risk"] == 0.0
        ]
        candidates = stable or model_rows
        selected.append(max(candidates, key=lambda row: row["best_score"]))
    return selected


def plot_best_by_model(rows: list[dict[str, Any]]) -> None:
    best_rows = recommended_rows(rows)
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=160)
    labels = [f"{row['model']} r{row['rank']}" for row in best_rows]
    values = [row["best_score"] for row in best_rows]
    bars = ax.bar(labels, values, color=["#2878b5", "#c85200"])
    ax.set_ylabel("Best score")
    ax.set_title("Recommended configuration by model")
    ax.grid(axis="y", alpha=0.25)
    for bar, row in zip(bars, best_rows, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"step {row['best_step']}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "recommended_config_by_model.jpg")
    plt.close(fig)


def markdown_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| Model | Rank | Best Step | Best Score | Final Score | JSON Valid | "
        "JSON Keys | Safety Risk | Postal Terms | Next Steps |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    lines = [header]
    for row in sorted(rows, key=lambda item: (item["model"], item["rank"])):
        lines.append(
            "| {model} | {rank} | {best_step} | {best_score:.4f} | {final_score:.4f} | "
            "{json_valid:.4f} | {json_keys:.4f} | {safety_risk:.4f} | "
            "{postal_terms:.4f} | {next_steps:.4f} |".format(**row)
        )
    return "\n".join(lines)


def write_report(rows: list[dict[str, Any]]) -> None:
    recommended = {row["model"]: row for row in recommended_rows(rows)}
    best_3b = recommended["3B"]
    best_7b = recommended["7B"]
    report = f"""# Qwen2.5 MLX SFT Global Compare

本报告由 `global_compare/build_global_compare.py` 从结构化 monitor 数据生成，不读取已有图片，也不从图片反推数据。

数据源：

```text
{RUNS['3B'].relative_to(ROOT)}
{RUNS['7B'].relative_to(ROOT)}
```

## Summary Table

{markdown_table(rows)}

## Key Findings

当前 3B 最优配置：

```text
Qwen2.5-3B-Instruct + LoRA rank {best_3b['rank']}
best_step={best_3b['best_step']}
best_score={best_3b['best_score']:.4f}
adapter={best_3b['adapter']}
```

当前 7B 最优配置：

```text
Qwen2.5-7B-Instruct + LoRA rank {best_7b['rank']}
best_step={best_7b['best_step']}
best_score={best_7b['best_score']:.4f}
adapter={best_7b['adapter']}
```

推荐配置不是只看瞬时 `best_score`，还要求 `json_keys > 0`、`score_drop <= 0.5` 且 `safety_risk = 0`。在这个稳定性约束下，3B 推荐 rank {best_3b['rank']}，7B 推荐 rank {best_7b['rank']}。这说明 LoRA rank 不能直接跨模型照搬，需要分别 sweep。

## Figures

### Best Score By Rank

![Best score by rank](plots/best_score_by_rank.jpg)

### Final Score By Rank

![Final score by rank](plots/final_score_by_rank.jpg)

### Score Drop By Rank

![Score drop by rank](plots/score_drop_by_rank.jpg)

### Postal Terms By Rank

![Postal terms by rank](plots/postal_terms_by_rank.jpg)

### Next Steps By Rank

![Next steps by rank](plots/next_steps_by_rank.jpg)

### Recommended Configuration By Model

![Recommended configuration by model](plots/recommended_config_by_model.jpg)
"""
    (OUT_DIR / "global_compare_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for model, run_dir in RUNS.items():
        rows.extend(summarize_run(model, run_dir))
    write_csv(rows)
    plot_metric(rows, "best_score", "Best score", "best_score_by_rank.jpg")
    plot_metric(rows, "final_score", "Final score", "final_score_by_rank.jpg")
    plot_metric(rows, "score_drop", "Best - final score", "score_drop_by_rank.jpg")
    plot_metric(rows, "postal_terms", "Postal term hits", "postal_terms_by_rank.jpg")
    plot_metric(rows, "next_steps", "Next-step hits", "next_steps_by_rank.jpg")
    plot_best_by_model(rows)
    write_report(rows)
    print(f"wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
