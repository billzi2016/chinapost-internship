"""管理原始抓取结果和结构化记录的本地落盘。"""

from __future__ import annotations

import json
import shutil
import threading
from dataclasses import asdict
from pathlib import Path

from crawler.models import FetchResult, PolicyRecord, RobotsDecision


class Storage:
    """封装数据目录和常用写入操作。"""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.parsed_dir = data_dir / "parsed"
        self.logs_dir = data_dir / "logs"
        self._write_lock = threading.Lock()

    def ensure_directories(self) -> None:
        """创建数据目录。

        目录创建被集中到这里，便于以后统一加入权限检查或路径规范。
        """

        for path in [self.data_dir, self.raw_dir, self.parsed_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def reset_data_dir(self) -> None:
        """清空并重建数据目录。

        这个操作只作用于项目自己的 `data/` 输出目录，
        用于开始一轮新的完整抓取，避免旧结果混入新结果。
        """

        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        self.ensure_directories()

    def append_robots_decision(self, decision: RobotsDecision) -> None:
        """记录 robots 校验结果。"""

        self._append_json_line(self.logs_dir / "robots_report.jsonl", asdict(decision))

    def append_fetch_result(self, result: FetchResult) -> None:
        """记录页面抓取结果。"""

        self._append_json_line(self.logs_dir / "fetch_results.jsonl", asdict(result))

    def append_robots_from_fetch_result(self, result: FetchResult) -> None:
        """从抓取结果中抽出 robots 决策并单独记录。

        这样即使某次抓取后来失败，合规判断也仍然有独立日志可追溯。
        """

        decision = {
            "url": result.url,
            "allowed": result.robots_allowed,
            "checked_at": result.fetched_at.isoformat(),
            "reason": result.robots_reason,
        }
        self._append_json_line(self.logs_dir / "robots_report.jsonl", decision)

    def append_policy_record(self, record: PolicyRecord) -> None:
        """记录解析后的政策结果。"""

        self._append_json_line(self.parsed_dir / "policies.jsonl", asdict(record))

    def _append_json_line(self, path: Path, payload: dict[str, object]) -> None:
        """以 JSONL 形式追加写入单条记录。"""

        with self._write_lock:
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=False, default=str))
                file.write("\n")
