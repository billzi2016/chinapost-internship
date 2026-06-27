"""项目入口脚本。

当前入口只负责:
- 读取配置。
- 初始化请求器、限速和存储。
- 执行第一批种子任务或 dry-run。

它不直接承担抓取细节，避免入口脚本不断膨胀。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from crawler.config_loader import load_rate_limits, load_sources
from crawler.fetcher import Fetcher
from crawler.offline_parser import parse_stored_fetches
from crawler.scheduler import run_seed_tasks
from crawler.storage import Storage


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="快递物流政策采集合规爬虫")
    parser.add_argument(
        "--config-dir",
        default="configs",
        help="配置目录路径，默认使用项目下的 configs",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="数据输出目录，默认使用项目下的 data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只展示将要处理的种子任务，不发起网络请求",
    )
    parser.add_argument(
        "--max-pages-per-source",
        type=int,
        default=3,
        help="每个来源最多处理的页面数，默认 3",
    )
    parser.add_argument(
        "--discovery-depth",
        type=int,
        default=1,
        help="链接发现深度，默认 1，表示抓首页并继续一层候选页面",
    )
    parser.add_argument(
        "--full-run",
        action="store_true",
        help="启用完整抓取模式，自动放大页面上限并清空旧输出目录",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="跨来源并发 worker 数，默认 4；同一来源内部仍保持串行",
    )
    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="只抓取并保存原始响应，不执行 parse/filter",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="不发起网络请求，只从 data/raw 和 fetch_results.jsonl 离线生成样本",
    )
    return parser


def resolve_runtime_options(args: argparse.Namespace) -> tuple[int, int, bool, int]:
    """根据命令行参数计算最终运行选项。

    `--full-run` 是给最终执行准备的一键模式，
    启用后会自动扩大抓取范围并刷新输出目录，避免旧数据残留。
    """

    if args.full_run:
        cpu_count = os.cpu_count() or 8
        auto_workers = max(4, cpu_count // 2)
        return 20, 2, True, auto_workers
    return args.max_pages_per_source, args.discovery_depth, False, args.max_workers


def main() -> int:
    """初始化组件并执行任务。"""

    args = build_argument_parser().parse_args()
    config_dir = Path(args.config_dir)
    data_dir = Path(args.data_dir)
    max_pages_per_source, discovery_depth, reset_output, max_workers = resolve_runtime_options(args)

    sources = load_sources(config_dir)

    storage = Storage(data_dir)
    if reset_output:
        storage.reset_data_dir()
    else:
        storage.ensure_directories()

    if args.parse_only:
        policy_count, filtered_count = parse_stored_fetches(sources, storage)
        print(f"[PARSE] policies={policy_count} filtered={filtered_count}")
        return 0

    default_rate_limit, domain_rate_limits = load_rate_limits(config_dir)

    fetcher = Fetcher(
        default_rate_limit=default_rate_limit,
        domain_rate_limits=domain_rate_limits,
    )

    summaries = run_seed_tasks(
        sources=sources,
        fetcher=fetcher,
        storage=storage,
        dry_run=args.dry_run,
        max_pages_per_source=max_pages_per_source,
        discovery_depth=discovery_depth,
        max_workers=max_workers,
        parse_during_crawl=not args.crawl_only,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
