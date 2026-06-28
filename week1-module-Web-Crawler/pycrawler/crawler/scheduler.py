"""提供任务生成与批量调度能力。

当前版本会先抓取入口页，再从成功页面中发现少量候选政策链接。
链接提取细节被拆到独立模块中，这里只负责任务队列、去重和执行顺序。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from crawler.dedupe import canonicalize_url
from crawler.faq_parser import parse_faq_json
from crawler.fetcher import Fetcher
from crawler.link_discovery import discover_policy_links
from crawler.models import CrawlTask, SourceConfig
from crawler.parser import parse_policy_page, parse_policy_pdf
from crawler.pdf_parser import extract_pdf_text
from crawler.progress import ProgressReporter
from crawler.reporting import write_crawl_report
from crawler.storage import Storage


def build_seed_tasks(sources: list[SourceConfig]) -> list[CrawlTask]:
    """根据来源配置构造第一批种子任务。"""

    tasks: list[CrawlTask] = []
    for source in sources:
        for entry_url in source.entry_urls:
            tasks.append(
                CrawlTask(
                    source_id=source.source_id,
                    company=source.company,
                    url=entry_url,
                    topic_hints=source.allowed_topics,
                    depth=0,
                )
            )
    return tasks


def run_seed_tasks(
    sources: list[SourceConfig],
    fetcher: Fetcher,
    storage: Storage,
    dry_run: bool = False,
    max_pages_per_source: int = 3,
    discovery_depth: int = 1,
    max_workers: int = 4,
    parse_during_crawl: bool = True,
) -> list[str]:
    """执行第一批种子任务。

    当前实现采用“跨来源并发、来源内串行”的方式：
    - 不会并发抓同一个来源的页面。
    - 可以同时抓多个不同来源，加快整体扫描速度。
    """

    summaries: list[str] = []
    summary_lock = threading.Lock()
    reporter = ProgressReporter()

    def emit(line: str) -> None:
        with summary_lock:
            summaries.append(line)
            print(line, flush=True)

    worker_count = max(1, min(max_workers, len(sources)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _run_single_source,
                source=source,
                fetcher=fetcher,
                storage=storage,
                reporter=reporter,
                dry_run=dry_run,
                max_pages_per_source=max_pages_per_source,
                discovery_depth=discovery_depth,
                parse_during_crawl=parse_during_crawl,
                emit=emit,
            )
            for source in sources
        ]
        for future in as_completed(futures):
            future.result()

    report_path = write_crawl_report(storage.data_dir)
    emit(f"[REPORT] generated={report_path}")
    return summaries


def _run_single_source(
    source: SourceConfig,
    fetcher: Fetcher,
    storage: Storage,
    reporter: ProgressReporter,
    dry_run: bool,
    max_pages_per_source: int,
    discovery_depth: int,
    parse_during_crawl: bool,
    emit,
) -> None:
    """串行处理单个来源的抓取队列。"""

    tasks = [
        CrawlTask(
            source_id=source.source_id,
            company=source.company,
            url=url,
            topic_hints=source.allowed_topics,
            depth=0,
        )
        for url in source.entry_urls
    ]
    visited: set[str] = set()
    stored_policy_urls: set[str] = set()
    stored_policy_fingerprints: set[tuple[str, str]] = set()
    completed = 0

    for endpoint in source.api_endpoints:
        if completed >= max_pages_per_source:
            break
        endpoint_url = str(endpoint["url"])
        method = str(endpoint.get("method", "GET")).upper()
        payload = endpoint.get("json", {})
        if dry_run:
            completed += 1
            emit(f"[DRY-RUN][api] {source.company}: {endpoint_url}")
            continue
        if method != "POST":
            emit(f"[API-SKIP] {source.company}: unsupported method={method} -> {endpoint_url}")
            continue
        result = fetcher.post_json(endpoint_url, dict(payload) if isinstance(payload, dict) else {})
        storage.append_fetch_result(
            result,
            source_id=source.source_id,
            company=source.company,
            parser_kind="faq_json",
        )
        completed += 1
        emit(
            f"[API][depth=0] {source.company}: {endpoint_url} -> "
            f"{result.status_code if result.status_code is not None else 'SKIP'}"
        )
        if not result.success or not parse_during_crawl:
            continue
        try:
            policy_records, filtered_records = parse_faq_json(source, endpoint_url, result.text)
        except Exception as exc:
            emit(f"[API-ERROR] {source.company}: {endpoint_url} -> {exc}")
            continue
        saved_count = 0
        for record in policy_records:
            fingerprint = (record.title, record.summary)
            if record.url in stored_policy_urls or fingerprint in stored_policy_fingerprints:
                continue
            stored_policy_urls.add(record.url)
            stored_policy_fingerprints.add(fingerprint)
            storage.append_policy_record(record)
            saved_count += 1
        for filtered_record in filtered_records:
            storage.append_filtered_page(filtered_record)
        emit(
            f"[API-PARSE] {source.company}: policies={saved_count} "
            f"filtered={len(filtered_records)} -> {endpoint_url}"
        )

    while tasks:
        task = tasks.pop(0)
        normalized_url = canonicalize_url(task.url)
        if normalized_url in visited:
            continue
        if completed >= max_pages_per_source:
            continue
        visited.add(normalized_url)

        if dry_run:
            completed += 1
            emit(f"[DRY-RUN][depth={task.depth}] {task.company}: {task.url}")
            emit(
                reporter.report(
                    stage="dry-run",
                    company=task.company,
                    url=task.url,
                    completed=0,
                    queued=len(tasks),
                )
            )
            continue

        result = fetcher.fetch(task.url)
        storage.append_fetch_result(
            result,
            source_id=task.source_id,
            company=task.company,
            parser_kind="html",
        )
        completed += 1
        emit(
            f"[FETCH][depth={task.depth}] {task.company}: {task.url} -> "
            f"{result.status_code if result.status_code is not None else 'SKIP'}"
        )
        emit(
            reporter.report(
                stage="fetch",
                company=task.company,
                url=task.url,
                completed=0,
                queued=len(tasks),
            )
        )

        if not result.success:
            continue
        content_type = result.content_type.lower()
        if "pdf" in content_type or result.final_url.lower().endswith(".pdf"):
            pdf_title = result.final_url.rsplit("/", 1)[-1] or f"{task.company} PDF"
            storage.save_pdf_bytes(
                source_id=task.source_id,
                company=task.company,
                url=result.final_url,
                title=pdf_title,
                body_bytes=result.body_bytes,
            )
            if not parse_during_crawl:
                continue

            try:
                pdf_text = extract_pdf_text(result.body_bytes)
            except Exception as exc:
                emit(f"[PDF-ERROR] {task.company}: {result.final_url} -> {exc}")
                continue

            policy_record, filtered_record = parse_policy_pdf(source, result.final_url, pdf_text)
            if filtered_record is not None:
                storage.append_filtered_page(filtered_record)
                emit(f"[FILTER][PDF] {task.company}: {filtered_record.filter_reason} -> {result.final_url}")
                continue
            if policy_record is not None:
                fingerprint = (policy_record.title, policy_record.summary)
                if (
                    policy_record.url in stored_policy_urls
                    or fingerprint in stored_policy_fingerprints
                ):
                    continue
                stored_policy_urls.add(policy_record.url)
                stored_policy_fingerprints.add(fingerprint)
                storage.append_policy_record(policy_record)
                emit(f"[PDF] {task.company}: parsed -> {result.final_url}")
            continue

        if "html" not in content_type:
            continue

        if parse_during_crawl:
            policy_record, filtered_record = parse_policy_page(source, task.url, result.text)
            if filtered_record is not None:
                storage.append_filtered_page(filtered_record)
                emit(f"[FILTER] {task.company}: {filtered_record.filter_reason} -> {task.url}")
            elif policy_record is not None:
                fingerprint = (policy_record.title, policy_record.summary)
                if policy_record.url in stored_policy_urls or fingerprint in stored_policy_fingerprints:
                    continue
                stored_policy_urls.add(policy_record.url)
                stored_policy_fingerprints.add(fingerprint)
                storage.append_policy_record(policy_record)

        if task.depth >= discovery_depth:
            continue

        discovered_links = discover_policy_links(
            task.url,
            result.text,
            allowed_domains=source.allowed_domains,
        )
        for link in discovered_links:
            if completed >= max_pages_per_source:
                break
            if link in visited:
                continue
            tasks.append(
                CrawlTask(
                    source_id=task.source_id,
                    company=task.company,
                    url=link,
                    topic_hints=task.topic_hints,
                    depth=task.depth + 1,
                )
            )
        if discovered_links:
            emit(f"[DISCOVER] {task.company}: discovered={len(discovered_links)} from {task.url}")
