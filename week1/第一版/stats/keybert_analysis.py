"""KeyBERT 关键词分析。

这里走的是语义嵌入路线：
先把清洗后的文本送进 KeyBERT，再根据语义相似度抽关键词。

注意：
当前实现刻意保持简洁，不强行把底层并行、batch 或设备控制
拧进来，避免这一层代码变得过重。
"""

import json
from pathlib import Path

from keyword_utils import TOP_K, ensure_output_dir, filter_document, get_all_documents

OUTPUT_DIRNAME = "keybert"

try:
    from keybert import KeyBERT
except ImportError:  # pragma: no cover
    # 缺少依赖时允许主流程继续运行，只跳过 KeyBERT 这一支。
    KeyBERT = None


def build_docs(documents):
    """把 token 列表重新拼回文本，供 KeyBERT 使用。"""
    return [" ".join(filter_document(document)) for document in documents if filter_document(document)]


def compute_keybert(documents, top_k=TOP_K):
    """执行 KeyBERT 关键词提取。"""
    if KeyBERT is None:
        return []
    docs = build_docs(documents)
    if not docs:
        return []
    # 这里保持官方最简调用方式，避免为了强行加控制项把代码写复杂。
    model = KeyBERT()
    keywords = model.extract_keywords(
        "\n".join(docs),
        keyphrase_ngram_range=(1, 2),
        stop_words=None,
        top_n=top_k,
    )
    return [{"token": token, "score": round(float(score), 6)} for token, score in keywords]


def save_keywords(results, output_dir):
    """保存 KeyBERT 输出。"""
    json_path = output_dir / "keybert_keywords.json"
    txt_path = output_dir / "keybert_keywords.txt"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    with txt_path.open("w", encoding="utf-8") as file:
        for split_name, keywords in results.items():
            file.write(f"===== {split_name} =====\n")
            for item in keywords:
                file.write(f"{item['token']}\tscore={item['score']}\n")
            file.write("\n")


def print_keywords(results):
    """打印 KeyBERT 结果。"""
    if KeyBERT is None:
        print("\nKeyBERT 未安装，已跳过 KeyBERT 关键词分析。")
        return
    for split_name, keywords in results.items():
        print(f"\n===== {split_name} KeyBERT =====")
        for item in keywords[:15]:
            print(f"{item['token']}: score={item['score']}")


def run_keybert_analysis(basic_results, output_base_dir):
    """执行 KeyBERT 分析主流程。"""
    output_dir = ensure_output_dir(output_base_dir, OUTPUT_DIRNAME)
    results = {}
    for split_name, metrics in basic_results.items():
        results[split_name] = compute_keybert(metrics.get("documents", []))
    results["all"] = compute_keybert(get_all_documents(basic_results))
    print_keywords(results)
    save_keywords(results, output_dir)
    return results


def main():
    """允许单独运行 KeyBERT 分析。"""
    from basic_analysis import run_basic_analysis
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    basic_results = run_basic_analysis(datasets, current_dir)
    run_keybert_analysis(basic_results, current_dir)


if __name__ == "__main__":
    main()
