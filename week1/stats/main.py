from pathlib import Path

from advanced_analysis import run_advanced_analysis
from basic_analysis import run_basic_analysis
from dataloader import load_datasets
from vis import generate_visualizations


def describe_dataset(name, dataset):
    sample_count = len(dataset)
    print(f"{name} 数据集:")
    print(f"  样本数: {sample_count}")

    if not dataset:
        print("  数据集为空\n")
        return

    first_sample = dataset[0]
    qa_count = len(first_sample.get("QA", []))
    dialogue_count = len(first_sample.get("Dialogue", []))
    fields = ", ".join(first_sample.keys())

    print(f"  第一条样本字段: {fields}")
    print(f"  第一条样本 QA 数量: {qa_count}")
    print(f"  第一条样本 Dialogue 数量: {dialogue_count}\n")


def main():
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)

    for split_name, dataset in datasets.items():
        describe_dataset(split_name, dataset)

    basic_results = run_basic_analysis(datasets, current_dir)
    advanced_results = run_advanced_analysis(basic_results, current_dir)
    generate_visualizations(basic_results, advanced_results, current_dir)


if __name__ == "__main__":
    main()
