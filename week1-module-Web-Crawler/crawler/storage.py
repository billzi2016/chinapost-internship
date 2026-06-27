"""管理原始抓取结果和结构化记录的本地落盘。"""

from __future__ import annotations

import json
import shutil
import threading
from dataclasses import asdict
from hashlib import sha1
from pathlib import Path

from crawler.models import FetchResult, FilteredPageRecord, PdfDownloadRecord, PolicyRecord


class Storage:
    """封装数据目录和常用写入操作。"""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.raw_pdf_dir = data_dir / "raw_pdfs"
        self.parsed_dir = data_dir / "parsed"
        self.logs_dir = data_dir / "logs"
        self._write_lock = threading.Lock()

    def ensure_directories(self) -> None:
        """创建数据目录。

        目录创建被集中到这里，便于以后统一加入权限检查或路径规范。
        """

        for path in [self.data_dir, self.raw_dir, self.raw_pdf_dir, self.parsed_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def reset_data_dir(self) -> None:
        """清空并重建数据目录。

        这个操作只作用于项目自己的 `data/` 输出目录，
        用于开始一轮新的完整抓取，避免旧结果混入新结果。
        """

        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        self.ensure_directories()

    def reset_parsed_outputs(self) -> None:
        """清空离线解析输出，保留已抓取的 raw 和 fetch 日志。"""

        for path in [
            self.parsed_dir / "policies.jsonl",
            self.parsed_dir / "training_samples.jsonl",
            self.logs_dir / "filtered_pages.jsonl",
        ]:
            if path.exists():
                path.unlink()

    def append_fetch_result(
        self,
        result: FetchResult,
        source_id: str = "",
        company: str = "",
        parser_kind: str = "html",
    ) -> None:
        """记录页面抓取结果。"""

        payload = asdict(result)
        text = result.text
        raw_text_path = ""
        if text:
            raw_text_path = str(self._write_raw_text(result.final_url or result.url, text, parser_kind))
        payload["source_id"] = source_id
        payload["company"] = company
        payload["parser_kind"] = parser_kind
        payload["raw_text_path"] = raw_text_path
        payload["text"] = text[:1000]
        payload["text_truncated"] = len(text) > 1000
        payload["body_bytes"] = f"<bytes:{len(result.body_bytes)}>"
        self._append_json_line(self.logs_dir / "fetch_results.jsonl", payload)

    def _write_raw_text(self, url: str, text: str, parser_kind: str) -> Path:
        """保存完整文本响应，供离线 parse/filter 反复使用。"""

        digest = sha1(f"{parser_kind}:{url}:{text[:200]}".encode("utf-8")).hexdigest()
        suffix = "json" if parser_kind == "faq_json" else "html"
        raw_path = self.raw_dir / f"{digest}.{suffix}"
        with self._write_lock:
            raw_path.write_text(text, encoding="utf-8")
        return raw_path

    def append_policy_record(self, record: PolicyRecord) -> None:
        """记录解析后的政策结果。"""

        self._append_json_line(self.parsed_dir / "policies.jsonl", asdict(record))
        self._append_json_line(self.parsed_dir / "training_samples.jsonl", asdict(record))

    def append_filtered_page(self, record: FilteredPageRecord) -> None:
        """记录被过滤掉的页面，不进入训练样本。"""

        self._append_json_line(self.logs_dir / "filtered_pages.jsonl", asdict(record))

    def save_pdf_bytes(
        self,
        source_id: str,
        company: str,
        url: str,
        title: str,
        body_bytes: bytes,
    ) -> Path:
        """保存原始 PDF 文件并记录元数据。

        文件名使用 URL 哈希，避免中文路径、查询串和同名覆盖问题。
        """

        digest = sha1(url.encode("utf-8")).hexdigest()
        pdf_path = self.raw_pdf_dir / f"{digest}.pdf"
        with self._write_lock:
            pdf_path.write_bytes(body_bytes)
        record = PdfDownloadRecord(
            source_id=source_id,
            company=company,
            url=url,
            title=title,
            saved_path=str(pdf_path),
        )
        self._append_json_line(self.logs_dir / "pdf_downloads.jsonl", asdict(record))
        return pdf_path

    def _append_json_line(self, path: Path, payload: dict[str, object]) -> None:
        """以 JSONL 形式追加写入单条记录。"""

        with self._write_lock:
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=False, default=str))
                file.write("\n")
