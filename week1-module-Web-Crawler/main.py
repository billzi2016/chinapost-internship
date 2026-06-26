"""项目入口脚本。

当前入口只负责:
- 读取配置。
- 初始化 robots、限速和存储。
- 执行第一批种子任务或 dry-run。

它不直接承担抓取细节，避免入口脚本不断膨胀。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from crawler.config_loader import load_rate_limits, load_sources
from crawler.fetcher import Fetcher
from crawler.robots import RobotsManager
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
    return parser


def main() -> int:
    """初始化组件并执行任务。"""

    args = build_argument_parser().parse_args()
    config_dir = Path(args.config_dir)
    data_dir = Path(args.data_dir)

    sources = load_sources(config_dir)
    default_rate_limit, domain_rate_limits = load_rate_limits(config_dir)

    storage = Storage(data_dir)
    storage.ensure_directories()

    fetcher = Fetcher(
        robots_manager=RobotsManager(),
        default_rate_limit=default_rate_limit,
        domain_rate_limits=domain_rate_limits,
    )

    summaries = run_seed_tasks(
        sources=sources,
        fetcher=fetcher,
        storage=storage,
        dry_run=args.dry_run,
    )
    for summary in summaries:
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
