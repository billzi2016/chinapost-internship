"""filter 模块的数据加载与文本拼接工具。

这里和 stats 共用同一份原始数据，
但 filter 额外需要把一条完整对话整理成单个文本，
方便后续做 embedding 和 LLM 二分类。
"""

import json
from pathlib import Path


def load_datasets(data_dir):
    """读取 train / val / test 三个 JSON。"""
    data_path = Path(data_dir)
    datasets = {}

    for split in ("train", "val", "test"):
        file_path = data_path / f"{split}.json"
        with file_path.open("r", encoding="utf-8") as file:
            datasets[split] = json.load(file)

    return datasets


def dialogue_to_text(sample):
    """把一条多轮对话拼成单个文本。

    输出格式保留 speaker 前缀，方便后续 embedding 和 LLM
    知道每一轮是谁在说话。
    """
    turns = []
    for turn in sample.get("Dialogue", []):
        speaker = turn.get("speaker", "")
        utterance = turn.get("utterance", "").strip()
        if utterance:
            turns.append(f"{speaker}: {utterance}")
    return "\n".join(turns)
