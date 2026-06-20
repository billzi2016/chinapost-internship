import json
import statistics
from pathlib import Path

import tiktoken

OUTPUT_DIRNAME = "basic_analysis"


def remove_spaces(text):
    return "".join(text.split())


def count_words(text):
    return len([token for token in text.strip().split() if token])


def collect_dialogue_metrics(dataset, encoding):
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
            metrics["words"].extend(utterance_words)
            document_tokens.extend(utterance_words)

        metrics["dialogue_token_counts"].append(dialogue_token_total)
        metrics["dialogue_word_counts"].append(dialogue_word_total)
        metrics["documents"].append(document_tokens)

    return metrics


def summarize(values):
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
    return {
        "对话轮数": summarize(metrics["turn_counts"]),
        "整条对话 token 数": summarize(metrics["dialogue_token_counts"]),
        "单轮 utterance token 数": summarize(metrics["utterance_token_counts"]),
        "整条对话词数": summarize(metrics["dialogue_word_counts"]),
        "单轮 utterance 词数": summarize(metrics["utterance_word_counts"]),
    }

def ensure_output_dir(base_dir):
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_basic_summary(results, output_dir):
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
    output_dir = ensure_output_dir(output_base_dir)
    encoding = tiktoken.get_encoding("cl100k_base")
    results = {}

    for split_name, dataset in datasets.items():
        metrics = collect_dialogue_metrics(dataset, encoding)
        results[split_name] = metrics
        print_summary(split_name, metrics)

    save_basic_summary(results, output_dir)
    return results


def main():
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    run_basic_analysis(datasets, current_dir)


if __name__ == "__main__":
    main()
