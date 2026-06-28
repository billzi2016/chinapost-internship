"""输出轻量级进度信息。

当前实现默认使用单行文本进度，避免引入额外依赖。
后续如果环境稳定安装了 tqdm，可以在这里统一切换，而不改调度器主逻辑。
"""

from __future__ import annotations

import threading
import time


class ProgressReporter:
    """根据已完成任务和队列长度输出阶段进度与 ETA。"""

    def __init__(self) -> None:
        self.started_at = time.monotonic()
        self._completed = 0
        self._lock = threading.Lock()

    def report(
        self,
        stage: str,
        company: str,
        url: str,
        completed: int,
        queued: int,
    ) -> str:
        """生成一条包含 ETA 的进度文本。"""

        with self._lock:
            if completed <= 0:
                self._completed += 1
                completed = self._completed
            elapsed = max(time.monotonic() - self.started_at, 0.001)
            average = elapsed / max(completed, 1)
            remaining = max(queued, 0)
            eta_seconds = int(average * remaining)
            return (
                f"[PROGRESS] stage={stage} company={company} completed={completed} "
                f"queued={queued} eta≈{eta_seconds}s url={url}"
            )
