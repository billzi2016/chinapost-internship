import json
import math
from collections import Counter
from pathlib import Path

OUTPUT_DIRNAME = "advanced_analysis"
TOP_K = 30
MIN_DOC_FREQ = 5
MAX_DOC_FREQ_RATIO = 0.45
STOPWORDS = {
    "的",
    "了",
    "是",
    "吗",
    "我",
    "你",
    "他",
    "她",
    "它",
    "有",
    "在",
    "给",
    "请",
    "还",
    "什么",
    "没有",
    "一个",
    "这个",
    "那个",
    "一下",
    "一种",
    "一些",
    "一下子",
    "一下下",
    "这样",
    "那样",
    "现在",
    "今天",
    "明天",
    "昨天",
    "这里",
    "那里",
    "自己",
    "一下吧",
    "一下哈",
    "一下哦",
    "可能",
    "因为",
    "所以",
    "如果",
    "但是",
    "而且",
    "或者",
    "还是",
    "然后",
    "就是",
    "那个",
    "这个",
    "已经",
    "还有",
    "一下子",
    "的话",
    "不用",
    "需要",
    "可以",
    "亲爱",
    "您好呀",
    "您好呢",
    "你好呀",
    "你好呢",
    "您",
    "你好",
    "您好",
    "好的",
    "好",
    "嗯",
    "呢",
    "哦",
    "哈",
    "啊",
    "呀",
    "吧",
    "哦哦",
    "亲",
    "亲亲",
    "请问",
    "麻烦",
    "稍等",
    "收到",
    "知道了",
    "可以",
    "这个",
    "那个",
    "一下",
    "这边",
    "那边",
    "已经",
    "帮",
    "帮您",
    "谢谢",
    "不用",
    "就是",
    "然后",
    "的话",
    "一下子",
    "就是",
    "还有",
    "我们",
    "你们",
    "他们",
    "进行",
    "处理",
    "问题",
    "咨询",
    "客户",
    "用户",
    "客服",
    "订单",
    "京东",
    "编号",
    "一下哈",
    "一下哦",
    "一下呢",
    "一下啊",
    "的话呢",
    "的话哦",
    "的话哈",
    "您好亲",
    "亲们",
    "小妹",
    "这会",
    "目前",
    "这边呢",
    "那边呢",
    "申请",
    "联系",
    "查询",
    "订单号",
}

SINGLE_CHAR_STOPWORDS = {
    "不",
    "为",
    "下",
    "到",
    "对",
    "就",
    "会",
    "要",
    "再",
    "能",
    "可",
    "把",
    "让",
    "从",
    "跟",
    "被",
    "将",
    "向",
    "和",
    "及",
    "与",
    "或",
}


def ensure_output_dir(base_dir):
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def normalize_token(token):
    token = token.strip().lower()
    if not token:
        return ""
    if token.startswith("[") and token.endswith("]"):
        return ""
    if token in STOPWORDS:
        return ""
    if token in SINGLE_CHAR_STOPWORDS:
        return ""
    if len(token) == 1 and not token.isalnum():
        return ""
    if len(token) == 1 and not ("\u4e00" <= token <= "\u9fff"):
        return ""
    if len(token) == 1:
        return ""
    if token.isdigit():
        return ""
    return token


def filter_document(tokens):
    filtered = []
    for token in tokens:
        normalized = normalize_token(token)
        if normalized:
            filtered.append(normalized)
    return filtered


def compute_tfidf(documents, top_k=TOP_K):
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
    for split_name, keywords in results.items():
        print(f"\n===== {split_name} TF-IDF =====")
        for item in keywords[:15]:
            print(
                f"{item['token']}: score={item['score']}, df={item['document_frequency']}"
            )


def run_advanced_analysis(basic_results, output_base_dir):
    output_dir = ensure_output_dir(output_base_dir)
    results = {}
    all_documents = []

    for split_name, metrics in basic_results.items():
        documents = metrics.get("documents", [])
        all_documents.extend(documents)
        results[split_name] = compute_tfidf(documents)

    results["all"] = compute_tfidf(all_documents)
    print_keywords(results)
    save_keywords(results, output_dir)
    return results


def main():
    from basic_analysis import run_basic_analysis
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    basic_results = run_basic_analysis(datasets, current_dir)
    run_advanced_analysis(basic_results, current_dir)


if __name__ == "__main__":
    main()
