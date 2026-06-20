"""读取 CSDS 三个 split 的基础数据加载器。

这个文件故意保持得很轻，只负责把 train / val / test
三个 JSON 文件读成 Python 对象，方便其他统计脚本复用。
"""

import json
from pathlib import Path


def load_datasets(data_dir):
    """读取给定目录下的 train/val/test 三个 JSON 数据集。"""
    data_path = Path(data_dir)
    datasets = {}

    # 这里固定按三个 split 读取，避免外部脚本各自重复拼路径。
    for split in ("train", "val", "test"):
        file_path = data_path / f"{split}.json"
        with file_path.open("r", encoding="utf-8") as file:
            datasets[split] = json.load(file)

    return datasets
