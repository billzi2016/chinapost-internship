"""CSDS 的基础统计分析。

这个模块负责输出最基础也最稳定的一层信息：
1. 对话轮数
2. 对话 token 数
3. 对话词数
4. 单轮 utterance 的 token / 词数

后续 TF-IDF、TextRank、KeyBERT 等高级关键词分析，
都会复用这里整理好的 `documents` 和 `words`。
"""

import json
import statistics
from pathlib import Path

import tiktoken

OUTPUT_DIRNAME = "basic_analysis"


def remove_spaces(text):
    """去掉所有空格，用于 token 长度统计。

    这里的口径是用户之前明确要求的：token 数统计前先去空格，
    再用 cl100k_base 编码。
    """
    return "".join(text.split())


def count_words(text):
    """统计词数。

    原始数据本身已经分词，所以这里直接按空格切分即可。
    """
    return len([token for token in text.strip().split() if token])


def collect_dialogue_metrics(dataset, encoding):
    """把单个 split 的所有基础统计量收集到一个字典中。

    特别注意：
    - `words` 用于后续词频图和普通词云
    - `documents` 以“单条完整对话”为粒度，供 TF-IDF / TextRank / KeyBERT 使用
    """
    metrics = {
        "turn_counts": [],
        "dialogue_token_counts": [],
        "utterance_token_counts": [],
        "dialogue_word_counts": [],
        "utterance_word_counts": [],
        "words": [],
        "documents": [],
    }

    for sample in dataset:
        dialogue = sample.get("Dialogue", [])
        metrics["turn_counts"].append(len(dialogue))

        # 这里按“整条对话”累计 token / 词数，
        # 而不是只看单轮 utterance。
        dialogue_token_total = 0
        dialogue_word_total = 0

        document_tokens = []
        for turn in dialogue:
            utterance = turn.get("utterance", "")
            no_space_text = remove_spaces(utterance)
            utterance_token_count = len(encoding.encode(no_space_text))
            utterance_word_count = count_words(utterance)
            utterance_words = [token for token in utterance.strip().split() if token]

            dialogue_token_total += utterance_token_count
            dialogue_word_total += utterance_word_count

            metrics["utterance_token_counts"].append(utterance_token_count)
            metrics["utterance_word_counts"].append(utterance_word_count)
            # `words` 保存全量 token 序列，方便后续直接做词频图和词云。
            metrics["words"].extend(utterance_words)
            # `document_tokens` 保存当前对话自己的 token 序列，
            # 让后续关键词方法保持“单条对话 = 一个 document”的粒度。
            document_tokens.extend(utterance_words)

        metrics["dialogue_token_counts"].append(dialogue_token_total)
        metrics["dialogue_word_counts"].append(dialogue_word_total)
        metrics["documents"].append(document_tokens)

    return metrics


def summarize(values):
    """对一个数值列表输出基础统计摘要。"""
    if not values:
        return {
            "count": 0,
            "mean": 0,
            "median": 0,
            "min": 0,
            "max": 0,
        }

    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min": min(values),
        "max": max(values),
    }


def print_summary(split_name, metrics):
    """把当前 split 的摘要打印到终端。"""
    print(f"\n===== {split_name} =====")
    summary_map = build_summary(metrics)

    for metric_name, summary in summary_map.items():
        print(
            f"{metric_name}: "
            f"count={summary['count']}, "
            f"mean={summary['mean']}, "
            f"median={summary['median']}, "
            f"min={summary['min']}, "
            f"max={summary['max']}"
        )


def build_summary(metrics):
    """把内部 metrics 转成更适合写入 JSON 的摘要结构。"""
    return {
        "对话轮数": summarize(metrics["turn_counts"]),
        "整条对话 token 数": summarize(metrics["dialogue_token_counts"]),
        "单轮 utterance token 数": summarize(metrics["utterance_token_counts"]),
        "整条对话词数": summarize(metrics["dialogue_word_counts"]),
        "单轮 utterance 词数": summarize(metrics["utterance_word_counts"]),
    }

def ensure_output_dir(base_dir):
    """确保基础统计的输出目录存在。"""
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_basic_summary(results, output_dir):
    """把基础统计结果保存成 summary.json。

    这里保存的是摘要信息，不保存所有中间数组，
    避免输出文件过大。
    """
    serializable = {}

    for split_name, metrics in results.items():
        serializable[split_name] = {
            "summary": build_summary(metrics),
            "sample_count": len(metrics["documents"]),
        }

    output_path = output_dir / "summary.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(serializable, file, ensure_ascii=False, indent=2)


def run_basic_analysis(datasets, output_base_dir):
    """执行基础统计主流程。"""
    output_dir = ensure_output_dir(output_base_dir)
    # cl100k_base 是这里约定的 token 编码口径。
    encoding = tiktoken.get_encoding("cl100k_base")
    results = {}

    for split_name, dataset in datasets.items():
        metrics = collect_dialogue_metrics(dataset, encoding)
        results[split_name] = metrics
        print_summary(split_name, metrics)

    save_basic_summary(results, output_dir)
    return results


def main():
    """允许单独运行基础统计脚本。"""
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    run_basic_analysis(datasets, current_dir)


if __name__ == "__main__":
    main()
