import json
import os
import time
from pathlib import Path
from urllib import error, request

import h5py
import numpy as np
from tqdm import tqdm

import config
from dataloader import dialogue_to_text

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:8b")
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "32"))
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


def ensure_output_dir(base_dir):
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_texts(dataset):
    texts = []
    metadata = []

    for index, sample in enumerate(dataset):
        text = dialogue_to_text(sample)
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


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(
            f"请求 Ollama 失败: {exc}. 请确认 `ollama serve` 正在运行。"
        ) from exc


def embed_batch(texts):
    payload = {
        "model": EMBED_MODEL,
        "input": texts,
    }
    response = post_json(f"{OLLAMA_URL}/api/embed", payload)
    embeddings = response.get("embeddings")
    if not embeddings:
        raise RuntimeError("Ollama `/api/embed` 没有返回 embeddings。")
    return np.asarray(embeddings, dtype=np.float32)


def ensure_split_dataset(h5_file, split_name, total_count, embedding_dim):
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
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(metadata_by_split, file, ensure_ascii=False, indent=2)


def encode_split_to_h5(split_name, dataset, h5_file):
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

    probe_dataset = h5_file.get(split_name)
    if probe_dataset is not None and probe_dataset.attrs.get("completed", 0) > 0:
        completed = int(probe_dataset.attrs["completed"])
        embedding_dim = probe_dataset.shape[1]
        split_dataset = ensure_split_dataset(h5_file, split_name, total_count, embedding_dim)
    else:
        first_end = min(EMBED_BATCH_SIZE, total_count)
        first_embeddings = embed_batch(texts[:first_end])
        embedding_dim = first_embeddings.shape[1]
        split_dataset = ensure_split_dataset(h5_file, split_name, total_count, embedding_dim)
        completed = int(split_dataset.attrs.get("completed", 0))

        if completed == 0:
            split_dataset[0:first_end] = first_embeddings
            split_dataset.attrs["completed"] = first_end
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

            split_dataset[start:end] = batch_embeddings
            split_dataset.attrs["completed"] = end
            h5_file.flush()
            start = end
            progress_bar.update(1)
            time.sleep(SLEEP_SECONDS)

    return split_dataset.shape, metadata


def run_embedding_store(datasets, output_base_dir):
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
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    run_embedding_store(datasets, current_dir)


if __name__ == "__main__":
    main()
