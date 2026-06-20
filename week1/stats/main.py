"""stats 总入口。

这个脚本只负责串联流程，不在这里堆复杂逻辑：
1. 读取数据
2. 展示基本维度
3. 跑基础统计
4. 跑 TF-IDF / TextRank / KeyBERT
5. 统一出图
"""

from pathlib import Path

from basic_analysis import run_basic_analysis
from dataloader import load_datasets
from keybert_analysis import run_keybert_analysis
from tfidf_analysis import run_advanced_analysis
from textrank_analysis import run_textrank_analysis
from vis import generate_visualizations


def describe_dataset(name, dataset):
    """打印单个 split 的最基础结构信息。"""
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
    """执行 stats 目录下的完整主流程。"""
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    for split_name, dataset in datasets.items():
        describe_dataset(split_name, dataset)

    basic_results = run_basic_analysis(datasets, current_dir)
    keyword_results = {
        "TFIDF": run_advanced_analysis(basic_results, current_dir),
        "TextRank": run_textrank_analysis(basic_results, current_dir),
        "KeyBERT": run_keybert_analysis(basic_results, current_dir),
    }
    generate_visualizations(basic_results, keyword_results, current_dir)


if __name__ == "__main__":
    main()
