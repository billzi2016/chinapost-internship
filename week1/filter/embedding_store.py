import json
import os
from pathlib import Path
from urllib import error, request

import h5py
import numpy as np
from tqdm import tqdm

import config
from dataloader import dialogue_to_text

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:8b")
EMBED_BATCH_SIZE = 128
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


def encode_split(dataset):
    texts, metadata = build_texts(dataset)
    batches = []

    total_batches = (len(texts) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    for start in tqdm(
        range(0, len(texts), EMBED_BATCH_SIZE),
        total=total_batches,
        desc="embedding batches",
        unit="batch",
    ):
        end = start + EMBED_BATCH_SIZE
        batch_embeddings = embed_batch(texts[start:end])
        batches.append(batch_embeddings)

    if not batches:
        return np.empty((0, 0), dtype=np.float32), metadata

    return np.concatenate(batches, axis=0), metadata


def save_h5(embeddings_by_split, output_path):
    with h5py.File(output_path, "w") as h5_file:
        for split_name, array in embeddings_by_split.items():
            h5_file.create_dataset(
                split_name,
                data=array,
                compression="gzip",
                compression_opts=1,
            )


def save_metadata(metadata_by_split, output_path):
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(metadata_by_split, file, ensure_ascii=False, indent=2)


def run_embedding_store(datasets, output_base_dir):
    output_dir = ensure_output_dir(output_base_dir)
    embeddings_by_split = {}
    metadata_by_split = {}

    for split_name, dataset in datasets.items():
        print(f"开始编码 {split_name}，样本数={len(dataset)}")
        embeddings, metadata = encode_split(dataset)
        embeddings_by_split[split_name] = embeddings
        metadata_by_split[split_name] = metadata
        print(f"{split_name} 编码完成，shape={embeddings.shape}")

    save_h5(embeddings_by_split, output_dir / OUTPUT_FILENAME)
    save_metadata(metadata_by_split, output_dir / METADATA_FILENAME)
    return output_dir / OUTPUT_FILENAME, metadata_by_split


def main():
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    run_embedding_store(datasets, current_dir)


if __name__ == "__main__":
    main()
