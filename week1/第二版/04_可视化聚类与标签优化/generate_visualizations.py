#!/usr/bin/env python3
"""Generate task 04 PCA / t-SNE / UMAP figures.

This script keeps two views separate:
1. Binary view: gray = other, red = postal / delivery related by existing 20B result.
2. Category view: use 120B category labels only for coloring business types.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import h5py
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

try:
    import umap
except ImportError:  # pragma: no cover
    umap = None


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[2]
DATA_DIR = PROJECT_DIR / "week2" / "data"
EMBEDDING_PATH = DATA_DIR / "embeddings" / "dialogue_embeddings.h5"
FILTER_PATH = DATA_DIR / "llm_filter" / "postal_filter_results.json"
REVIEW_PATH = (
    PROJECT_DIR
    / "week1"
    / "第二版"
    / "01_分类效果评估与边界case分析"
    / "outputs"
    / "120b_broad_review_results.json"
)
OUTPUT_DIR = SCRIPT_DIR / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
SPLITS = ("train", "val", "test")
N_JOBS = max((os.cpu_count() or 1) - 2, 1)

FONT_CANDIDATES = (
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)

CATEGORY_ORDER = [
    "费率价格类",
    "时限时效类",
    "流程规则类",
    "禁限寄类",
    "国际业务类",
    "泛物流配送类",
    "非邮政相关",
    "解析失败",
]

CATEGORY_COLORS = {
    "费率价格类": "#2F6B7C",
    "时限时效类": "#D9822B",
    "流程规则类": "#D1495B",
    "禁限寄类": "#7C3AED",
    "国际业务类": "#1F7A5C",
    "泛物流配送类": "#C2410C",
    "非邮政相关": "#B8B8B8",
    "解析失败": "#6B7280",
}


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"未找到输入文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def configure_matplotlib() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    if any(Path(path).exists() for path in FONT_CANDIDATES):
        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Heiti SC", "Songti SC"]


def load_embeddings() -> np.ndarray:
    arrays = []
    with h5py.File(EMBEDDING_PATH, "r") as h5_file:
        for split in SPLITS:
            arrays.append(h5_file[split][:])
    return np.concatenate(arrays, axis=0)


def load_binary_mask() -> np.ndarray:
    filter_results = load_json(FILTER_PATH)
    masks = []
    for split in SPLITS:
        split_mask = [bool(item["is_postal_related"]) for item in filter_results[split]]
        masks.append(np.asarray(split_mask, dtype=bool))
    return np.concatenate(masks, axis=0)


def normalize_category(item: dict[str, Any]) -> str:
    if item.get("gpt_oss_120b_parse_error"):
        return "解析失败"
    label = item.get("gpt_oss_120b_label") or {}
    category = label.get("category") or item.get("category")
    if category in CATEGORY_COLORS:
        return category
    if label.get("broad_related") is False:
        return "非邮政相关"
    return "泛物流配送类"


def load_categories() -> np.ndarray:
    records = load_json(REVIEW_PATH)
    expected = []
    for split in SPLITS:
        split_records = [item for item in records if item.get("split") == split]
        split_records.sort(key=lambda item: int(item["index"]))
        expected.extend(normalize_category(item) for item in split_records)
    return np.asarray(expected, dtype=object)


def run_pca(embeddings: np.ndarray) -> np.ndarray:
    return PCA(n_components=2, random_state=42).fit_transform(embeddings)


def run_tsne(embeddings: np.ndarray) -> np.ndarray:
    return TSNE(
        n_components=2,
        random_state=42,
        init="pca",
        perplexity=30,
        n_jobs=N_JOBS,
    ).fit_transform(embeddings)


def run_umap(embeddings: np.ndarray) -> np.ndarray | None:
    if umap is None:
        return None
    return umap.UMAP(n_components=2, random_state=42, n_jobs=N_JOBS).fit_transform(embeddings)


def save_binary_scatter(points: np.ndarray, mask: np.ndarray, title: str, output_path: Path) -> None:
    other_count = int((~mask).sum())
    related_count = int(mask.sum())
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(
        points[~mask, 0],
        points[~mask, 1],
        s=7,
        alpha=0.28,
        c="#B8B8B8",
        linewidths=0,
        label=f"其他 (n={other_count})",
    )
    ax.scatter(
        points[mask, 0],
        points[mask, 1],
        s=8,
        alpha=0.72,
        c="#D1495B",
        linewidths=0,
        label=f"邮政/快递相关 (n={related_count})",
    )
    ax.set_title(title, fontsize=18, pad=12)
    ax.set_xlabel("Component 1", fontsize=12)
    ax.set_ylabel("Component 2", fontsize=12)
    ax.legend(fontsize=11, loc="best", frameon=True, markerscale=1.8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def save_category_scatter(points: np.ndarray, categories: np.ndarray, title: str, output_path: Path) -> None:
    counts = Counter(categories.tolist())
    fig, ax = plt.subplots(figsize=(11.5, 8))
    for category in CATEGORY_ORDER:
        if category not in counts:
            continue
        mask = categories == category
        is_other = category in {"非邮政相关", "解析失败"}
        ax.scatter(
            points[mask, 0],
            points[mask, 1],
            s=6 if is_other else 10,
            alpha=0.22 if is_other else 0.78,
            c=CATEGORY_COLORS[category],
            linewidths=0,
            label=f"{category} (n={counts[category]})",
        )
    ax.set_title(title, fontsize=18, pad=12)
    ax.set_xlabel("Component 1", fontsize=12)
    ax.set_ylabel("Component 2", fontsize=12)
    ax.legend(
        fontsize=10,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=True,
        markerscale=2.4,
        scatterpoints=1,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def generate() -> list[Path]:
    configure_matplotlib()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    embeddings = load_embeddings()
    binary_mask = load_binary_mask()
    categories = load_categories()

    if len(binary_mask) != len(embeddings):
        raise ValueError(f"20B mask 数量不匹配：{len(binary_mask)} != {len(embeddings)}")
    if len(categories) != len(embeddings):
        raise ValueError(f"120B category 数量不匹配：{len(categories)} != {len(embeddings)}")

    reducers = {
        "pca": ("PCA", run_pca),
        "tsne": ("t-SNE", run_tsne),
        "umap": ("UMAP", run_umap),
    }
    generated = []
    for method_key, (method_name, reducer) in reducers.items():
        points = reducer(embeddings)
        if points is None:
            print("UMAP 依赖未安装，跳过 UMAP 图。")
            continue
        binary_path = FIGURE_DIR / f"all_{method_key}_binary.png"
        category_path = FIGURE_DIR / f"all_{method_key}_120b_category.png"
        save_binary_scatter(points, binary_mask, f"全量样本 {method_name}：20B 二分类", binary_path)
        save_category_scatter(points, categories, f"全量样本 {method_name}：120B 业务类别染色", category_path)
        generated.extend([binary_path, category_path])

    summary = {
        "total": int(len(embeddings)),
        "binary_counts": {
            "postal_related": int(binary_mask.sum()),
            "other": int((~binary_mask).sum()),
        },
        "category_counts": dict(Counter(categories.tolist())),
        "figures": [str(path.relative_to(OUTPUT_DIR)) for path in generated],
    }
    (OUTPUT_DIR / "visualization_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="生成 04 可视化图片")
    return parser.parse_args()


def main() -> None:
    parse_args()
    generated = generate()
    for path in generated:
        print(path)


if __name__ == "__main__":
    main()
