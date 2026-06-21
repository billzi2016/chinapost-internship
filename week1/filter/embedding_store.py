"""对话级 embedding 生成与 HDF5 分块续写。

这个模块最关键的目标有两个：
1. 把每条完整对话编码成向量
2. 尽量稳地写盘，支持中断后从断点继续

这里故意不用“算完全部 embedding 再一次性写文件”的方式，
而是按 batch 切片写入固定 shape 的 HDF5 dataset，
避免重复重写前面已经完成的数据。
"""

import json
import os
import time
from pathlib import Path

import h5py
import numpy as np
import ollama
from tqdm import tqdm

import config
from dataloader import dialogue_to_text

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:8b")
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "8"))
WRITE_BATCH_SIZE = int(os.environ.get("WRITE_BATCH_SIZE", "32"))
EMBED_PREFIX = os.environ.get(
    "EMBED_PREFIX",
    (
        "Instruct: Represent the following Chinese customer service dialogue "
        "for topic filtering, clustering, and semantic analysis.\n"
        "Text: "
    ),
)
OUTPUT_DIRNAME = "embeddings"
OUTPUT_FILENAME = "dialogue_embeddings.h5"
METADATA_FILENAME = "dialogue_metadata.json"
SLEEP_SECONDS = 0.5
OLLAMA_CLIENT = ollama.Client(host=OLLAMA_URL)


def ensure_output_dir(base_dir):
    """确保 embedding 输出目录存在。"""
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_texts(dataset):
    """把一个 split 的样本整理成待编码文本和元信息。"""
    texts = []
    metadata = []

    for index, sample in enumerate(dataset):
        text = dialogue_to_text(sample)
        # 这里的 instruction 前缀是“存储侧 embedding”语义，
        # 用于让向量更偏向主题筛选、聚类和语义表示。
        if EMBED_PREFIX:
            text = f"{EMBED_PREFIX}{text}"
        texts.append(text)
        metadata.append(
            {
                "index": index,
                "session_id": sample.get("Session_id"),
                "dialogue_id": sample.get("DialogueID"),
                "turn_count": len(sample.get("Dialogue", [])),
            }
        )

    return texts, metadata


def embed_batch(texts):
    """用官方 ollama Python 库对一个 batch 做 embedding。"""
    try:
        response = OLLAMA_CLIENT.embed(model=EMBED_MODEL, input=texts)
    except Exception as exc:
        raise RuntimeError(
            f"请求 Ollama embed 失败: {exc}. 请确认 `ollama serve` 正在运行，"
            f"并检查模型 `{EMBED_MODEL}` 是否可用。"
        ) from exc

    embeddings = response.get("embeddings")
    if not embeddings:
        raise RuntimeError("ollama.Client.embed(...) 没有返回 embeddings。")
    return np.asarray(embeddings, dtype=np.float32)


def flush_embedding_buffer(split_dataset, start_index, buffer_arrays, h5_file):
    """把内存里暂存的一批 embedding 一次性切片写入 HDF5。"""
    if not buffer_arrays:
        return start_index

    merged = np.concatenate(buffer_arrays, axis=0)
    end_index = start_index + merged.shape[0]
    split_dataset[start_index:end_index] = merged
    split_dataset.attrs["completed"] = end_index
    h5_file.flush()
    return end_index


def ensure_split_dataset(h5_file, split_name, total_count, embedding_dim):
    """确保某个 split 对应的 HDF5 dataset 已经存在且 shape 正确。

    `completed` 属性用于记录这个 split 已经写到第几条，
    这是断点续跑的关键状态。
    """
    if split_name not in h5_file:
        dataset = h5_file.create_dataset(
            split_name,
            shape=(total_count, embedding_dim),
            dtype=np.float32,
            compression="gzip",
            compression_opts=1,
        )
        dataset.attrs["completed"] = 0
        return dataset

    dataset = h5_file[split_name]
    if dataset.shape != (total_count, embedding_dim):
        raise RuntimeError(
            f"{split_name} 数据集 shape 不匹配，现有 {dataset.shape}，"
            f"预期 {(total_count, embedding_dim)}。请检查旧 h5 是否需要删除。"
        )
    if "completed" not in dataset.attrs:
        dataset.attrs["completed"] = 0
    return dataset


def save_metadata(metadata_by_split, output_path):
    """保存对话索引、session_id 等元信息，方便后续追溯。"""
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(metadata_by_split, file, ensure_ascii=False, indent=2)


def encode_split_to_h5(split_name, dataset, h5_file):
    """把单个 split 编码后分块写入 HDF5。"""
    texts, metadata = build_texts(dataset)
    total_count = len(texts)

    if total_count == 0:
        if split_name not in h5_file:
            empty_dataset = h5_file.create_dataset(
                split_name,
                shape=(0, 0),
                dtype=np.float32,
                compression="gzip",
                compression_opts=1,
            )
            empty_dataset.attrs["completed"] = 0
        return (0, 0), metadata

    # 如果这个 split 之前已经写过一部分，就直接从断点继续。
    probe_dataset = h5_file.get(split_name)
    if probe_dataset is not None and probe_dataset.attrs.get("completed", 0) > 0:
        completed = int(probe_dataset.attrs["completed"])
        embedding_dim = probe_dataset.shape[1]
        split_dataset = ensure_split_dataset(h5_file, split_name, total_count, embedding_dim)
    else:
        # 第一次运行时先用首个 batch 探测 embedding 维度，
        # 这样后面才能安全地创建固定 shape 的 dataset。
        first_end = min(EMBED_BATCH_SIZE, total_count)
        first_embeddings = embed_batch(texts[:first_end])
        embedding_dim = first_embeddings.shape[1]
        split_dataset = ensure_split_dataset(h5_file, split_name, total_count, embedding_dim)
        completed = int(split_dataset.attrs.get("completed", 0))

        if completed == 0:
            split_dataset[0:first_end] = first_embeddings
            split_dataset.attrs["completed"] = first_end
            # 每次写完立刻 flush，尽量减少中断时的丢失窗口。
            h5_file.flush()
            completed = first_end
            time.sleep(SLEEP_SECONDS)

    total_batches = (total_count + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    completed_batches = completed // EMBED_BATCH_SIZE

    with tqdm(
        total=total_batches,
        initial=completed_batches,
        desc=f"{split_name} embedding batches",
        unit="batch",
    ) as progress_bar:
        start = completed
        buffer_arrays = []
        pending_count = 0

        while start < total_count:
            end = min(start + EMBED_BATCH_SIZE, total_count)
            batch_embeddings = embed_batch(texts[start:end])

            if batch_embeddings.shape[0] != end - start:
                raise RuntimeError(
                    f"{split_name} batch 返回条数不匹配: "
                    f"expected={end - start}, got={batch_embeddings.shape[0]}"
                )
            if batch_embeddings.shape[1] != split_dataset.shape[1]:
                raise RuntimeError(
                    f"{split_name} embedding 维度不匹配: "
                    f"expected={split_dataset.shape[1]}, got={batch_embeddings.shape[1]}"
                )

            # 这里把“请求批次”和“写盘批次”拆开：
            # - 请求 Ollama 时尽量小，降低服务端崩溃概率
            # - 写 HDF5 时尽量按较大的块落盘，减少 flush 频率
            buffer_arrays.append(batch_embeddings)
            pending_count += batch_embeddings.shape[0]

            if pending_count >= WRITE_BATCH_SIZE:
                completed = flush_embedding_buffer(
                    split_dataset, completed, buffer_arrays, h5_file
                )
                buffer_arrays = []
                pending_count = 0

            start = end
            progress_bar.update(1)
            time.sleep(SLEEP_SECONDS)

        if buffer_arrays:
            completed = flush_embedding_buffer(
                split_dataset, completed, buffer_arrays, h5_file
            )

    return split_dataset.shape, metadata


def run_embedding_store(datasets, output_base_dir):
    """执行 embedding 主流程，并对三个 split 逐个续跑。"""
    output_dir = ensure_output_dir(output_base_dir)
    h5_path = output_dir / OUTPUT_FILENAME
    metadata_by_split = {}

    with h5py.File(h5_path, "a") as h5_file:
        for split_name, dataset in datasets.items():
            print(f"开始编码 {split_name}，样本数={len(dataset)}")
            shape, metadata = encode_split_to_h5(split_name, dataset, h5_file)
            metadata_by_split[split_name] = metadata
            print(f"{split_name} 编码完成，shape={shape}")

    save_metadata(metadata_by_split, output_dir / METADATA_FILENAME)
    return h5_path, metadata_by_split


def main():
    """允许单独运行 embedding_store。"""
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    run_embedding_store(datasets, current_dir)


if __name__ == "__main__":
    main()
