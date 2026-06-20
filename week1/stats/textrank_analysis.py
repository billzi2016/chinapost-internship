import json
from collections import Counter, defaultdict
from pathlib import Path

from keyword_utils import TOP_K, ensure_output_dir, filter_document, get_all_documents

OUTPUT_DIRNAME = "textrank"
WINDOW_SIZE = 4
DAMPING = 0.85
ITERATIONS = 30


def build_graph(documents):
    graph = defaultdict(set)
    for document in documents:
        tokens = filter_document(document)
        for index, token in enumerate(tokens):
            for other in tokens[index + 1 : index + WINDOW_SIZE]:
                if token == other:
                    continue
                graph[token].add(other)
                graph[other].add(token)
    return graph


def run_pagerank(graph):
    scores = {node: 1.0 for node in graph}
    for _ in range(ITERATIONS):
        new_scores = {}
        for node, neighbors in graph.items():
            incoming = 0.0
            for neighbor in neighbors:
                incoming += scores[neighbor] / (len(graph[neighbor]) or 1)
            new_scores[node] = (1 - DAMPING) + DAMPING * incoming
        scores = new_scores
    return scores


def compute_textrank(documents, top_k=TOP_K):
    graph = build_graph(documents)
    if not graph:
        return []
    scores = run_pagerank(graph)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    token_counts = Counter()
    for document in documents:
        token_counts.update(filter_document(document))
    return [
        {"token": token, "score": round(score, 6), "count": token_counts[token]}
        for token, score in ranked
    ]


def save_keywords(results, output_dir):
    json_path = output_dir / "textrank_keywords.json"
    txt_path = output_dir / "textrank_keywords.txt"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    with txt_path.open("w", encoding="utf-8") as file:
        for split_name, keywords in results.items():
            file.write(f"===== {split_name} =====\n")
            for item in keywords:
                file.write(f"{item['token']}\tscore={item['score']}\tcount={item['count']}\n")
            file.write("\n")


def print_keywords(results):
    for split_name, keywords in results.items():
        print(f"\n===== {split_name} TextRank =====")
        for item in keywords[:15]:
            print(f"{item['token']}: score={item['score']}, count={item['count']}")


def run_textrank_analysis(basic_results, output_base_dir):
    output_dir = ensure_output_dir(output_base_dir, OUTPUT_DIRNAME)
    results = {}
    for split_name, metrics in basic_results.items():
        results[split_name] = compute_textrank(metrics.get("documents", []))
    results["all"] = compute_textrank(get_all_documents(basic_results))
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
    run_textrank_analysis(basic_results, current_dir)


if __name__ == "__main__":
    main()
