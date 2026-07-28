"""TF-IDF 关键词分析。

这里保留一个传统、可解释、可控的统计基线。
相比词频法，TF-IDF 至少能把“在所有对话里都很常见”的词压下去。
"""

import json
import math
from collections import Counter
from pathlib import Path

from keyword_utils import (
    MAX_DOC_FREQ_RATIO,
    MIN_DOC_FREQ,
    TOP_K,
    ensure_output_dir,
    filter_document,
    get_all_documents,
)

OUTPUT_DIRNAME = "tfidf"


def compute_tfidf(documents, top_k=TOP_K):
    """按“单条对话 = 一个 document”计算 TF-IDF 关键词。"""
    filtered_documents = [filter_document(document) for document in documents]
    filtered_documents = [document for document in filtered_documents if document]
    if not filtered_documents:
        return []

    document_frequency = Counter()
    term_frequencies = []
    for document in filtered_documents:
        counter = Counter(document)
        term_frequencies.append(counter)
        document_frequency.update(counter.keys())

    document_count = len(filtered_documents)
    aggregate_scores = Counter()
    # 过于常见的词即使合法，也通常不是“能区分主题”的关键词，
    # 所以这里继续做一个上限过滤。
    max_doc_freq = max(int(document_count * MAX_DOC_FREQ_RATIO), 1)

    for counter in term_frequencies:
        total_terms = sum(counter.values())
        for token, count in counter.items():
            df = document_frequency[token]
            if df < MIN_DOC_FREQ or df > max_doc_freq:
                continue
            tf = count / total_terms
            idf = math.log((1 + document_count) / (1 + df)) + 1
            aggregate_scores[token] += tf * idf

    ranked = aggregate_scores.most_common(top_k)
    return [
        {
            "token": token,
            "score": round(score, 6),
            "document_frequency": document_frequency[token],
        }
        for token, score in ranked
    ]


def save_keywords(results, output_dir):
    """同时保存 JSON 和 TXT，方便后续程序读取和人工浏览。"""
    json_path = output_dir / "tfidf_keywords.json"
    txt_path = output_dir / "tfidf_keywords.txt"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    with txt_path.open("w", encoding="utf-8") as file:
        for split_name, keywords in results.items():
            file.write(f"===== {split_name} =====\n")
            for item in keywords:
                file.write(
                    f"{item['token']}\tscore={item['score']}\tdf={item['document_frequency']}\n"
                )
            file.write("\n")


def print_keywords(results):
    """在终端打印每个 split 的前若干个关键词。"""
    for split_name, keywords in results.items():
        print(f"\n===== {split_name} TF-IDF =====")
        for item in keywords[:15]:
            print(f"{item['token']}: score={item['score']}, df={item['document_frequency']}")


def run_advanced_analysis(basic_results, output_base_dir):
    """执行 TF-IDF 分析主流程。"""
    output_dir = ensure_output_dir(output_base_dir, OUTPUT_DIRNAME)
    results = {}
    for split_name, metrics in basic_results.items():
        results[split_name] = compute_tfidf(metrics.get("documents", []))
    results["all"] = compute_tfidf(get_all_documents(basic_results))
    print_keywords(results)
    save_keywords(results, output_dir)
    return results


def main():
    """允许单独运行 TF-IDF 分析。"""
    from basic_analysis import run_basic_analysis
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    basic_results = run_basic_analysis(datasets, current_dir)
    run_advanced_analysis(basic_results, current_dir)


if __name__ == "__main__":
    main()
