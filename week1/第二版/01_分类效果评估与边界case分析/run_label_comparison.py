#!/usr/bin/env python3
"""Compare regex weak labels, gpt-oss:20b binary labels, and gpt-oss:120b review labels.

Usage examples:

  python run_label_comparison.py --limit 50
  python run_label_comparison.py --split train --limit 200 --model gpt-oss:120b
  python run_label_comparison.py --no-ollama --limit 0

The script does not modify source data. It writes analysis outputs to the selected
output directory.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tqdm import tqdm


SCRIPT_DIR = Path(__file__).resolve().parent


def find_project_dir(start: Path) -> Path:
    """Find the project root relative to this script.

    The expected project root contains both week1 and week2. This keeps the
    script portable if the whole project directory is moved.
    """

    for current in [start, *start.parents]:
        if (current / "week1").is_dir() and (current / "week2").is_dir():
            return current
    raise FileNotFoundError("Cannot find project root containing both week1 and week2")


PROJECT_DIR = find_project_dir(SCRIPT_DIR)
DATA_DIR = PROJECT_DIR / "week2" / "data"
CSDS_DIR = DATA_DIR / "CSDS"
FILTER_RESULTS = DATA_DIR / "llm_filter" / "postal_filter_results.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs"


POSTAL_EXPLICIT_RE = re.compile(
    r"邮政|中国邮政|EMS|ems|邮局|邮政快递|邮政包裹|特快专递|挂号信|平邮|邮政编码|邮政网点|邮政营业厅|商务件"
)

DELIVERY_CANDIDATE_RE = re.compile(
    r"快递|物流|配送|派送|配送员|快递员|送货员|站点|分站|网点|自提点|提货点|派件点|配送点|"
    r"分拣|分拨|分部|揽收|取件|上门取件|上门取货|签收|拒收|收货|收件|寄回|寄出|寄送|"
    r"邮寄|包裹|运费险|运费|发货|到货|送达|送到|清关|海关|转站点|拦截|代收|货到付款"
)

BUSINESS_PATTERNS: dict[str, re.Pattern[str]] = {
    "费率价格类": re.compile(r"运费|邮费|多少钱|价格|费用|收费|保价|报价|首重|续重"),
    "时限时效类": re.compile(r"几天|多久|什么时候到|时效|预计|送达|到达|延误|超时|派送|物流|快递"),
    "流程规则类": re.compile(
        r"怎么寄|怎么下单|修改地址|地址写错|取消|退回|签收|揽收|取件|上门|站点|网点|流程|规则"
    ),
    "禁限寄类": re.compile(r"禁寄|限寄|不能寄|可以寄吗|违禁|液体|电池|药品|食品|化妆品|危险品"),
    "国际业务类": re.compile(r"国际|国外|海外|海关|清关|报关|跨境|进口|出口"),
}

ALLOWED_120B_CATEGORIES = [
    "费率价格类",
    "时限时效类",
    "流程规则类",
    "禁限寄类",
    "国际业务类",
    "泛物流配送类",
    "非邮政相关",
]

BROAD_RELATED_DEFINITION = (
    "判断给定对话是否和快递、物流、配送、邮政、EMS、运费、签收、揽收、退费、地址修改等相关。"
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def record_key(record: dict[str, Any]) -> str:
    return f"{record['split']}:{record['index']}"


def extract_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("FinalSumm", "UserSumm", "AgentSumm"):
        value = row.get(key) or []
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item is not None)
        elif value:
            parts.append(str(value))

    for qa in row.get("QA") or []:
        for key in ("QueSumm", "AnsSummShort", "AnsSummLong", "QASumm", "intent"):
            value = qa.get(key)
            if value:
                parts.append(str(value))

    return "；".join(parts)


def dialogue_preview(row: dict[str, Any], max_chars: int = 260) -> str:
    turns = []
    for turn in row.get("Dialogue") or []:
        speaker = turn.get("speaker", "")
        utterance = turn.get("utterance", "")
        turns.append(f"{speaker}: {utterance}")
    text = " | ".join(turns)
    return text[:max_chars]


def regex_label(text: str) -> dict[str, Any]:
    regex_related = bool(POSTAL_EXPLICIT_RE.search(text) or DELIVERY_CANDIDATE_RE.search(text))
    categories = [name for name, pattern in BUSINESS_PATTERNS.items() if pattern.search(text)]
    return {
        "regex_related": regex_related,
        "regex_categories": categories,
        "regex_category": categories[0] if categories else "未命中",
    }


def build_records(splits: list[str]) -> list[dict[str, Any]]:
    filter_data = load_json(FILTER_RESULTS)
    records: list[dict[str, Any]] = []

    for split in splits:
        csds_rows = load_json(CSDS_DIR / f"{split}.json")
        filter_rows = filter_data.get(split, [])
        by_index = {item["index"]: item for item in filter_rows}

        for index, row in enumerate(csds_rows):
            filter_item = by_index.get(index)
            if not filter_item:
                continue

            text = extract_text(row)
            weak = regex_label(text)
            is_20b_related = bool(filter_item.get("is_postal_related"))
            needs_120b_review = (
                is_20b_related != weak["regex_related"]
                or (is_20b_related and not weak["regex_categories"])
            )

            records.append(
                {
                    "split": split,
                    "index": index,
                    "dialogue_id": row.get("DialogueID"),
                    "session_id": row.get("Session_id"),
                    "gpt_oss_20b_related": is_20b_related,
                    "gpt_oss_20b_raw_response": filter_item.get("raw_response"),
                    **weak,
                    "needs_120b_review": needs_120b_review,
                    "summary_text": text[:900],
                    "dialogue_preview": dialogue_preview(row),
                }
            )

    return records


def ollama_generate(
    prompt: str,
    model: str,
    host: str,
    timeout: int,
    temperature: float,
    think: str | bool | None,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if think is not None:
        payload["think"] = think
    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data.get("response", ""))


def parse_json_object(text: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = text.strip()
    if "```" in cleaned:
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None, "response does not contain a JSON object"

    candidate = cleaned[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse failed: {exc}"

    if not isinstance(parsed, dict):
        return None, "parsed JSON is not an object"
    return parsed, None


def make_120b_prompt(record: dict[str, Any]) -> str:
    allowed = "、".join(ALLOWED_120B_CATEGORIES)
    return f"""你是一个严格的中文客服数据分类器和业务分类器。请独立判断样本是否相关，并进一步细分业务类。

只输出一个 JSON 对象，不要输出 Markdown，不要输出解释性正文。

二分类定义：
{BROAD_RELATED_DEFINITION}

字段要求：
- broad_related: boolean。若样本符合上面的二分类定义，则 broad_related=true；否则 broad_related=false。
- category: string，只能取这些值之一：{allowed}
- reason: string，一句话说明判断依据。
- confidence: number，0 到 1。

样本：
- split: {record["split"]}
- index: {record["index"]}
- dialogue_id: {record["dialogue_id"]}
- summary: {record["summary_text"]}
- dialogue_preview: {record["dialogue_preview"]}
"""


def review_with_120b(
    records: list[dict[str, Any]],
    model: str,
    host: str,
    timeout: int,
    temperature: float,
    think: str | bool | None,
    sleep_seconds: float,
    save_every: int,
    output_jsonl: Path,
    completed_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    reviewed: list[dict[str, Any]] = []
    buffer: list[dict[str, Any]] = []
    completed_keys = completed_keys or set()
    pending_records = [record for record in records if record_key(record) not in completed_keys]

    for record in tqdm(pending_records, desc=f"120B review ({model})", unit="sample"):
        prompt = make_120b_prompt(record)
        started = time.time()
        try:
            raw = ollama_generate(
                prompt,
                model=model,
                host=host,
                timeout=timeout,
                temperature=temperature,
                think=think,
            )
            parsed, error = parse_json_object(raw)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raw = ""
            parsed = None
            error = f"Ollama request failed: {exc}"

        elapsed = round(time.time() - started, 3)
        item = {
            **record,
            "gpt_oss_120b_model": model,
            "gpt_oss_120b_elapsed_seconds": elapsed,
            "gpt_oss_120b_raw": raw,
            "gpt_oss_120b_parse_error": error,
            "gpt_oss_120b_label": parsed,
        }
        reviewed.append(item)
        buffer.append(item)

        if len(buffer) >= save_every:
            append_jsonl(output_jsonl, buffer)
            buffer.clear()

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    append_jsonl(output_jsonl, buffer)
    return reviewed


def summarize(records: list[dict[str, Any]], reviewed: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    by_split: dict[str, Counter[str]] = defaultdict(Counter)
    regex_category_counts: Counter[str] = Counter()
    disagreement_counts: Counter[str] = Counter()

    for record in records:
        split = record["split"]
        by_split[split]["total"] += 1
        by_split[split]["gpt_oss_20b_related"] += int(record["gpt_oss_20b_related"])
        by_split[split]["regex_related"] += int(record["regex_related"])
        by_split[split]["needs_120b_review"] += int(record["needs_120b_review"])
        for category in record["regex_categories"] or ["未命中"]:
            regex_category_counts[category] += 1
        key = f"20b={record['gpt_oss_20b_related']} regex={record['regex_related']}"
        disagreement_counts[key] += 1

    summary: dict[str, Any] = {
        "by_split": {split: dict(counter) for split, counter in by_split.items()},
        "regex_category_counts": dict(regex_category_counts),
        "twenty_b_vs_regex_counts": dict(disagreement_counts),
    }

    if reviewed is not None:
        category_counts: Counter[str] = Counter()
        broad_counts: Counter[str] = Counter()
        twenty_b_vs_120b_counts: Counter[str] = Counter()
        regex_vs_120b_counts: Counter[str] = Counter()
        parse_errors = 0
        for item in reviewed:
            label = item.get("gpt_oss_120b_label")
            if isinstance(label, dict):
                category_counts[str(label.get("category", "未知"))] += 1
                broad_value = label.get("broad_related")
                broad_counts[str(broad_value)] += 1
                if isinstance(broad_value, bool):
                    twenty_b_vs_120b_counts[
                        f"20b={item['gpt_oss_20b_related']} 120b={broad_value}"
                    ] += 1
                    regex_vs_120b_counts[
                        f"regex={item['regex_related']} 120b={broad_value}"
                    ] += 1
            else:
                parse_errors += 1
        summary["gpt_oss_120b_review"] = {
            "total": len(reviewed),
            "category_counts": dict(category_counts),
            "broad_related_counts": dict(broad_counts),
            "twenty_b_vs_120b_counts": dict(twenty_b_vs_120b_counts),
            "regex_vs_120b_counts": dict(regex_vs_120b_counts),
            "parse_errors": parse_errors,
        }

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["train", "val", "test", "all"], default="all")
    parser.add_argument("--limit", type=int, default=50, help="Number of samples to send to 120B review.")
    parser.add_argument("--model", default="gpt-oss:120b")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--think",
        choices=["low", "medium", "high"],
        default="low",
        help='Ollama thinking mode for gpt-oss models. Default: "low".',
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--save-every", type=int, default=100, help="Flush 120B JSONL results every N samples.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-ollama", action="store_true", help="Only compute 20B vs regex summary.")
    parser.add_argument(
        "--review-policy",
        choices=["disagreement", "20b-related", "regex-related", "all"],
        default="disagreement",
        help="Which samples should be reviewed by 120B.",
    )
    return parser.parse_args()


def select_review_records(records: list[dict[str, Any]], policy: str, limit: int) -> list[dict[str, Any]]:
    if policy == "disagreement":
        selected = [record for record in records if record["needs_120b_review"]]
    elif policy == "20b-related":
        selected = [record for record in records if record["gpt_oss_20b_related"]]
    elif policy == "regex-related":
        selected = [record for record in records if record["regex_related"]]
    else:
        selected = list(records)

    if limit > 0:
        return selected[:limit]
    return selected


def main() -> None:
    args = parse_args()
    splits = ["train", "val", "test"] if args.split == "all" else [args.split]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = build_records(splits)
    dump_json(args.output_dir / "20b_vs_regex_records.json", records)

    review_records = select_review_records(records, args.review_policy, args.limit)
    dump_json(args.output_dir / "120b_broad_review_candidates.json", review_records)

    review_jsonl = args.output_dir / "120b_broad_review_results.jsonl"
    existing_reviewed = read_jsonl(review_jsonl)
    completed_keys = {record_key(item) for item in existing_reviewed if "split" in item and "index" in item}
    reviewed: list[dict[str, Any]] | None = existing_reviewed if existing_reviewed else None

    if not args.no_ollama and review_records:
        new_reviewed = review_with_120b(
            review_records,
            model=args.model,
            host=args.ollama_host,
            timeout=args.timeout,
            temperature=args.temperature,
            think=args.think,
            sleep_seconds=args.sleep_seconds,
            save_every=max(1, args.save_every),
            output_jsonl=review_jsonl,
            completed_keys=completed_keys,
        )
        reviewed = [*existing_reviewed, *new_reviewed]
        dump_json(args.output_dir / "120b_broad_review_results.json", reviewed)

    summary = summarize(records, reviewed)
    dump_json(args.output_dir / "label_comparison_summary.json", summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n输出目录：{args.output_dir}")


if __name__ == "__main__":
    main()
