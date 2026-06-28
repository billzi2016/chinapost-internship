"""从已保存的原始抓取结果离线生成训练样本。"""

from __future__ import annotations

import json
from pathlib import Path

from crawler.faq_parser import parse_faq_json
from crawler.models import SourceConfig
from crawler.parser import parse_policy_page
from crawler.reporting import write_crawl_report
from crawler.storage import Storage


def parse_stored_fetches(sources: list[SourceConfig], storage: Storage) -> tuple[int, int]:
    """读取 fetch 日志和 raw 文本，离线执行 parse/filter。"""

    source_by_id = {source.source_id: source for source in sources}
    fetch_log = storage.logs_dir / "fetch_results.jsonl"

    policy_records_to_write = []
    filtered_records_to_write = []
    seen_fingerprints: set[tuple[str, str]] = set()
    seen_urls: set[str] = set()

    if not fetch_log.exists():
        write_crawl_report(storage.data_dir)
        return 0, 0

    with fetch_log.open("r", encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            if row.get("success") is not True:
                continue

            source = source_by_id.get(str(row.get("source_id", "")))
            if source is None:
                continue

            raw_text = _read_raw_text(row)
            if not raw_text:
                continue

            parser_kind = str(row.get("parser_kind", "html"))
            url = str(row.get("final_url") or row.get("url") or "")
            if parser_kind == "faq_json":
                records, filtered = parse_faq_json(source, url, raw_text)
                for record in records:
                    if _already_seen(record.url, record.title, record.summary, seen_urls, seen_fingerprints):
                        continue
                    policy_records_to_write.append(record)
                for filtered_record in filtered:
                    filtered_records_to_write.append(filtered_record)
                continue

            record, filtered_record = parse_policy_page(source, url, raw_text)
            if record is not None:
                if _already_seen(record.url, record.title, record.summary, seen_urls, seen_fingerprints):
                    continue
                policy_records_to_write.append(record)
            elif filtered_record is not None:
                filtered_records_to_write.append(filtered_record)

    if not policy_records_to_write and not filtered_records_to_write:
        write_crawl_report(storage.data_dir)
        return 0, 0

    storage.reset_parsed_outputs()
    for record in policy_records_to_write:
        storage.append_policy_record(record)
    for filtered_record in filtered_records_to_write:
        storage.append_filtered_page(filtered_record)
    write_crawl_report(storage.data_dir)
    return len(policy_records_to_write), len(filtered_records_to_write)


def _read_raw_text(row: dict[str, object]) -> str:
    """优先读取完整 raw 文件，兼容旧日志中的 text 预览。"""

    raw_path = str(row.get("raw_text_path") or "")
    if raw_path:
        path = Path(raw_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
    return str(row.get("text") or "")


def _already_seen(
    url: str,
    title: str,
    summary: str,
    seen_urls: set[str],
    seen_fingerprints: set[tuple[str, str]],
) -> bool:
    """按 URL 和正文指纹同时去重。"""

    fingerprint = (title, summary)
    if url in seen_urls or fingerprint in seen_fingerprints:
        return True
    seen_urls.add(url)
    seen_fingerprints.add(fingerprint)
    return False
