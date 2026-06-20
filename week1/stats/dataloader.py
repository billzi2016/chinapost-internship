import json
from pathlib import Path


def load_datasets(data_dir):
    data_path = Path(data_dir)
    datasets = {}

    for split in ("train", "val", "test"):
        file_path = data_path / f"{split}.json"
        with file_path.open("r", encoding="utf-8") as file:
            datasets[split] = json.load(file)

    return datasets
