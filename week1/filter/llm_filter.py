import json
import os
import time
from pathlib import Path
from urllib import error, request

import config
from dataloader import dialogue_to_text
from tqdm import tqdm

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
FILTER_MODEL = os.environ.get("FILTER_MODEL", "gpt-oss:20b")
OUTPUT_DIRNAME = "llm_filter"
OUTPUT_FILENAME = "postal_filter_results.json"
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 1
SYSTEM_PROMPT = (
    "你是一个严格的中文客服数据分类器。"
    "判断给定对话是否和快递、物流、配送、邮政、EMS、运费、签收、揽收、退费、地址修改等相关。"
    "如果相关，只输出 true。"
    "如果不相关，只输出 false。"
    "禁止输出其他任何内容。"
)


def ensure_output_dir(base_dir):
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(
            f"请求 Ollama 失败: {exc}. 请确认 `ollama serve` 正在运行。"
        ) from exc


def classify_dialogue(text):
    payload = {
        "model": FILTER_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "options": {"temperature": 0},
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = post_json(f"{OLLAMA_URL}/api/chat", payload)
            message = response.get("message", {})
            content = message.get("content", "").strip().lower()
            normalized = content.replace(" ", "")
            if normalized == "true":
                return True, content
            if normalized == "false":
                return False, content
            last_error = RuntimeError(f"模型返回不是 true/false: {content}")
        except RuntimeError as exc:
            last_error = exc

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_SLEEP_SECONDS)

    raise RuntimeError(
        f"分类失败，已重试 {MAX_RETRIES} 次。最后一次错误: {last_error}"
    )


def save_results(results, output_path):
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)


def run_llm_filter(datasets, output_base_dir):
    output_dir = ensure_output_dir(output_base_dir)
    results = {}

    for split_name, dataset in datasets.items():
        split_results = []
        positive_count = 0

        for index, sample in enumerate(
            tqdm(dataset, desc=f"{split_name} llm filter", unit="dialogue")
        ):
            text = dialogue_to_text(sample)
            is_related, raw_response = classify_dialogue(text)
            if is_related:
                positive_count += 1

            split_results.append(
                {
                    "index": index,
                    "session_id": sample.get("Session_id"),
                    "dialogue_id": sample.get("DialogueID"),
                    "is_postal_related": is_related,
                    "raw_response": raw_response,
                }
            )

        results[split_name] = split_results
        print(
            f"{split_name} 过滤完成: {positive_count}/{len(split_results)} 条被判定为快递/邮政相关"
        )

    save_results(results, output_dir / OUTPUT_FILENAME)
    return results


def main():
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    run_llm_filter(datasets, current_dir)


if __name__ == "__main__":
    main()
