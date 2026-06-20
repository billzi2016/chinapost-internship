"""filter 模块的降维可视化。

这里的图主要用来回答两个问题：
1. 全量对话在 embedding 空间里大致怎么分布
2. 被 LLM 判定为快递/邮政相关的对话，是否形成可见的聚类区域
"""

import json
import os
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

try:
    import umap
except ImportError:  # pragma: no cover
    umap = None

TITLE_SIZE = 22
LABEL_SIZE = 16
TICK_SIZE = 13
OUTPUT_DIRNAME = "vis"
EMBED_FILENAME = "dialogue_embeddings.h5"
FILTER_FILENAME = "postal_filter_results.json"
N_JOBS = max((os.cpu_count() or 1) - 2, 1)


def ensure_output_dir(base_dir):
    """确保降维图输出目录存在。"""
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_embeddings(h5_path):
    """读取 HDF5 中三个 split 的 embedding。"""
    embeddings = {}
    with h5py.File(h5_path, "r") as h5_file:
        for split_name in ("train", "val", "test"):
            embeddings[split_name] = h5_file[split_name][:]
    return embeddings


def load_filter_results(json_path):
    """读取 LLM 过滤结果。"""
    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_selected_mask(split_results):
    """把过滤结果转成布尔 mask，方便绘图时区分两类点。"""
    return np.asarray(
        [item["is_postal_related"] for item in split_results],
        dtype=bool,
    )


def save_scatter(points, mask, title, output_path):
    """保存二维散点图。

    颜色约定：
    - 灰色：其他对话
    - 红色：被筛出的快递/邮政相关对话
    """
    plt.figure(figsize=(10, 8))
    plt.scatter(
        points[~mask, 0],
        points[~mask, 1],
        s=10,
        alpha=0.35,
        c="#B8B8B8",
        label="全部数据中的其他对话",
    )
    plt.scatter(
        points[mask, 0],
        points[mask, 1],
        s=12,
        alpha=0.8,
        c="#D1495B",
        label="筛出的快递/邮政相关对话",
    )
    plt.title(title, fontsize=TITLE_SIZE)
    plt.xlabel("Component 1", fontsize=LABEL_SIZE)
    plt.ylabel("Component 2", fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def run_pca(embeddings):
    """执行 PCA，作为线性降维基线。"""
    reducer = PCA(n_components=2, random_state=42)
    return reducer.fit_transform(embeddings)


def run_tsne(embeddings):
    """执行 t-SNE。

    这里的 n_jobs 设置为 CPU 核数减 2，
    尽量减少把整机资源吃满的风险。
    """
    reducer = TSNE(
        n_components=2,
        random_state=42,
        init="pca",
        perplexity=30,
        n_jobs=N_JOBS,
    )
    return reducer.fit_transform(embeddings)


def run_umap(embeddings):
    """执行 UMAP；如果没装依赖则直接跳过。"""
    if umap is None:
        return None
    reducer = umap.UMAP(n_components=2, random_state=42, n_jobs=N_JOBS)
    return reducer.fit_transform(embeddings)


def combine_splits(embeddings_by_split, filter_results):
    """把 train / val / test 合并成一套全量 embedding 与 mask。"""
    arrays = []
    masks = []

    for split_name in ("train", "val", "test"):
        arrays.append(embeddings_by_split[split_name])
        masks.append(get_selected_mask(filter_results[split_name]))

    return np.concatenate(arrays, axis=0), np.concatenate(masks, axis=0)


def generate_visualizations(output_base_dir):
    """执行 filter 模块的完整降维可视化流程。"""
    output_dir = ensure_output_dir(output_base_dir)
    embeddings_dir = output_base_dir / "outputs" / "embeddings"
    filter_dir = output_base_dir / "outputs" / "llm_filter"
    embeddings_by_split = load_embeddings(embeddings_dir / EMBED_FILENAME)
    filter_results = load_filter_results(filter_dir / FILTER_FILENAME)

    # 先分别画 train / val / test，再画 all，方便既看局部也看全局。
    for split_name in ("train", "val", "test"):
        embeddings = embeddings_by_split[split_name]
        mask = get_selected_mask(filter_results[split_name])

        save_scatter(
            run_pca(embeddings),
            mask,
            f"{split_name} PCA",
            output_dir / f"{split_name}_pca.png",
        )
        save_scatter(
            run_tsne(embeddings),
            mask,
            f"{split_name} t-SNE",
            output_dir / f"{split_name}_tsne.png",
        )
        umap_points = run_umap(embeddings)
        if umap_points is not None:
            save_scatter(
                umap_points,
                mask,
                f"{split_name} UMAP",
                output_dir / f"{split_name}_umap.png",
            )

    all_embeddings, all_mask = combine_splits(embeddings_by_split, filter_results)
    save_scatter(
        run_pca(all_embeddings),
        all_mask,
        "all PCA",
        output_dir / "all_pca.png",
    )
    save_scatter(
        run_tsne(all_embeddings),
        all_mask,
        "all t-SNE",
        output_dir / "all_tsne.png",
    )
    all_umap = run_umap(all_embeddings)
    if all_umap is not None:
        save_scatter(
            all_umap,
            all_mask,
            "all UMAP",
            output_dir / "all_umap.png",
        )
    elif umap is None:
        print("未安装 `umap-learn`，UMAP 图已跳过。")


def main():
    """允许单独运行降维可视化。"""
    current_dir = Path(__file__).resolve().parent
    generate_visualizations(current_dir)


if __name__ == "__main__":
    main()
