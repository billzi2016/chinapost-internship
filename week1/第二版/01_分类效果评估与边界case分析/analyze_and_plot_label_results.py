#!/usr/bin/env python3
"""Generate analysis tables and figures from label comparison outputs.

This script is intentionally offline: it only reads existing JSON outputs from
run_label_comparison.py and does not call Ollama or modify source data.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs"
DEFAULT_FIGURE_DIRNAME = "figures"

FONT_CANDIDATES = (
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)

CATEGORY_ORDER = [
    "非邮政相关",
    "泛物流配送类",
    "流程规则类",
    "时限时效类",
    "费率价格类",
    "国际业务类",
    "禁限寄类",
    "未命中",
]

COLORS = {
    "20b": "#D1495B",
    "regex": "#2F6B7C",
    "bar": "#386FA4",
}

MATRIX_CMAP = LinearSegmentedColormap.from_list(
    "postal_matrix",
    ["#F8FAFC", "#BBD3E9", "#4E89B8", "#1F5F8B"],
)


def add_vertical_headroom(values: list[int | float], ratio: float = 0.16) -> None:
    """Leave room for value labels above bars."""

    if not values:
        return
    max_value = max(values)
    if max_value <= 0:
        return
    plt.ylim(0, max_value * (1 + ratio))


def add_horizontal_headroom(values: list[int | float], ratio: float = 0.12) -> None:
    """Leave room for value labels at the end of horizontal bars."""

    if not values:
        return
    max_value = max(values)
    if max_value <= 0:
        return
    plt.xlim(0, max_value * (1 + ratio))


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"未找到输入文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_font_path() -> str | None:
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return font_path
    return None


def configure_matplotlib() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    if get_font_path():
        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Heiti SC", "Songti SC"]


def pct(numerator: int | float, denominator: int | float) -> str:
    if not denominator:
        return "0.00%"
    return f"{numerator / denominator * 100:.2f}%"


def sorted_counter_items(counter: dict[str, int]) -> list[tuple[str, int]]:
    known = [(name, counter[name]) for name in CATEGORY_ORDER if name in counter]
    rest = sorted((name, value) for name, value in counter.items() if name not in CATEGORY_ORDER)
    return [*known, *rest]


def save_grouped_split_bar(summary: dict[str, Any], output_path: Path) -> None:
    splits = list(summary["by_split"].keys())
    totals = [summary["by_split"][split]["total"] for split in splits]
    related = [summary["by_split"][split]["gpt_oss_20b_related"] for split in splits]
    regex_related = [
        summary["by_split"][split].get("regex_related", 0)
        for split in splits
    ]

    x = range(len(splits))
    width = 0.32
    plt.figure(figsize=(11, 6.5))
    plt.bar([i - width / 2 for i in x], related, width=width, color=COLORS["20b"], label="20B 判为相关")
    plt.bar([i + width / 2 for i in x], regex_related, width=width, color=COLORS["regex"], label="Regex 命中")
    add_vertical_headroom([*related, *regex_related])
    for i, total in enumerate(totals):
        plt.text(i - width / 2, related[i], f"{pct(related[i], total)}", ha="center", va="bottom", fontsize=10)
        plt.text(i + width / 2, regex_related[i], f"{pct(regex_related[i], total)}", ha="center", va="bottom", fontsize=10)
    plt.title("各 split 标签规模对比", fontsize=18)
    plt.xlabel("数据划分", fontsize=13)
    plt.ylabel("样本数", fontsize=13)
    plt.xticks(list(x), splits, fontsize=12)
    plt.yticks(fontsize=11)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def save_binary_matrix(
    counts: dict[str, int],
    row_label: str,
    col_label: str,
    title: str,
    output_path: Path,
) -> None:
    matrix = [
        [
            int(counts.get(f"{row_label}=True {col_label}=True", 0)),
            int(counts.get(f"{row_label}=True {col_label}=False", 0)),
        ],
        [
            int(counts.get(f"{row_label}=False {col_label}=True", 0)),
            int(counts.get(f"{row_label}=False {col_label}=False", 0)),
        ],
    ]
    total = sum(sum(row) for row in matrix)

    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    image = ax.imshow(matrix, cmap=MATRIX_CMAP)
    ax.set_title(title, fontsize=18, pad=14)
    ax.set_xlabel(col_label, fontsize=13)
    ax.set_ylabel(row_label, fontsize=13)
    ax.set_xticks([0, 1], labels=["True", "False"], fontsize=12)
    ax.set_yticks([0, 1], labels=["True", "False"], fontsize=12)

    max_value = max(max(row) for row in matrix) if total else 0
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            text_color = "white" if max_value and value >= max_value * 0.55 else "#111827"
            ax.text(
                col_index,
                row_index,
                f"{value}\n{pct(value, total)}",
                ha="center",
                va="center",
                fontsize=14,
                color=text_color,
                fontweight="bold",
            )

    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=10)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def save_matrix_bar(summary: dict[str, Any], output_path: Path) -> None:
    counts = summary["twenty_b_vs_regex_counts"]
    save_binary_matrix(counts, "20b", "regex", "20B 二分类与 Regex 对比", output_path)


def save_horizontal_bar(counter: dict[str, int], title: str, output_path: Path) -> None:
    items = sorted_counter_items(counter)
    if not items:
        return
    labels = [item[0] for item in items]
    values = [item[1] for item in items]
    total = sum(values)

    height = max(5.2, 0.48 * len(labels) + 1.8)
    plt.figure(figsize=(11, height))
    bars = plt.barh(labels, values, color=COLORS["bar"])
    plt.gca().invert_yaxis()
    add_horizontal_headroom(values)
    for bar, value in zip(bars, values):
        plt.text(value, bar.get_y() + bar.get_height() / 2, f" {value} ({pct(value, total)})", va="center", fontsize=10)
    plt.title(title, fontsize=18)
    plt.xlabel("样本数", fontsize=13)
    plt.ylabel("类别", fontsize=13)
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_analysis_markdown(summary: dict[str, Any]) -> str:
    split_rows = []
    for split, item in summary["by_split"].items():
        total = int(item["total"])
        related = int(item["gpt_oss_20b_related"])
        regex_related = int(item.get("regex_related", 0))
        review = int(item["needs_120b_review"])
        split_rows.append(
            [
                split,
                str(total),
                f"{related} ({pct(related, total)})",
                f"{regex_related} ({pct(regex_related, total)})",
            ]
        )

    matrix_counts = summary["twenty_b_vs_regex_counts"]
    matrix_total = sum(int(value) for value in matrix_counts.values())
    matrix_rows = [
        [key, str(value), pct(int(value), matrix_total)]
        for key, value in matrix_counts.items()
    ]

    regex_counts = summary["regex_category_counts"]
    regex_total = sum(int(value) for value in regex_counts.values())
    regex_rows = [
        [name, str(value), pct(value, regex_total)]
        for name, value in sorted_counter_items(regex_counts)
    ]

    return f"""# 分类效果评估与边界 case 分析产物

## 1. 各 split 标签规模

{markdown_table(["split", "总样本数", "20B 判为相关", "Regex 命中"], split_rows)}

图表：`figures/20b_by_split.png`

## 2. 20B 与 Regex 对比

{markdown_table(["标签组合", "样本数", "占比"], matrix_rows)}

图表：`figures/20b_vs_regex_matrix.png`

## 3. regex 业务类弱标签分布

{markdown_table(["类别", "命中数", "占比"], regex_rows)}

图表：`figures/regex_category_counts.png`
"""


def write_markdown(output_path: Path, content: str) -> None:
    output_path.write_text(content, encoding="utf-8")


def generate_outputs(output_dir: Path, figure_dirname: str) -> None:
    configure_matplotlib()
    summary = load_json(output_dir / "label_comparison_summary.json")
    figure_dir = output_dir / figure_dirname
    figure_dir.mkdir(parents=True, exist_ok=True)

    save_grouped_split_bar(summary, figure_dir / "20b_by_split.png")
    save_matrix_bar(summary, figure_dir / "20b_vs_regex_matrix.png")
    save_horizontal_bar(summary["regex_category_counts"], "regex 业务类弱标签分布", figure_dir / "regex_category_counts.png")

    write_markdown(output_dir / "analysis_tables.md", build_analysis_markdown(summary))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="run_label_comparison.py 的输出目录")
    parser.add_argument("--figure-dirname", default=DEFAULT_FIGURE_DIRNAME, help="图片输出子目录名")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_outputs(args.output_dir, args.figure_dirname)
    print(f"分析表格已生成：{args.output_dir / 'analysis_tables.md'}")
    print(f"图表目录已生成：{args.output_dir / args.figure_dirname}")


if __name__ == "__main__":
    main()
