"""提供任务生成与批量调度能力。

第一版只处理来源入口页，不扩展页面内链接发现。
后续如果增加候选链接提取，应继续在调度层组装任务，不把控制逻辑塞进请求器。
"""

from __future__ import annotations

from crawler.fetcher import Fetcher
from crawler.models import CrawlTask, SourceConfig
from crawler.parser import parse_policy_page
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
                )
            )
    return tasks


def run_seed_tasks(
    sources: list[SourceConfig],
    fetcher: Fetcher,
    storage: Storage,
    dry_run: bool = False,
) -> list[str]:
    """执行第一批种子任务。

    返回:
    - 任务执行日志摘要，方便入口脚本直接打印。
    """

    tasks = build_seed_tasks(sources)
    source_map = {source.source_id: source for source in sources}
    summaries: list[str] = []

    for task in tasks:
        if dry_run:
            summaries.append(f"[DRY-RUN] {task.company}: {task.url}")
            continue

        result = fetcher.fetch(task.url)
        storage.append_fetch_result(result)
        summaries.append(
            f"[FETCH] {task.company}: {task.url} -> "
            f"{result.status_code if result.status_code is not None else 'SKIP'}"
        )

        if not result.success:
            continue

        source = source_map[task.source_id]
        policy_record = parse_policy_page(source, task.url, result.text)
        storage.append_policy_record(policy_record)

    return summaries
