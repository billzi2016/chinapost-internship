"""测试抓取报告生成逻辑。"""

from pathlib import Path

from crawler.reporting import build_crawl_report


def test_build_crawl_report_contains_summary_sections(tmp_path: Path) -> None:
    """报告中应包含总览、来源统计和失败统计。"""

    logs_dir = tmp_path / "logs"
    parsed_dir = tmp_path / "parsed"
    logs_dir.mkdir(parents=True)
    parsed_dir.mkdir(parents=True)

    (logs_dir / "fetch_results.jsonl").write_text(
        '{"url":"https://www.sf-express.com/","success":true,"failure_reason":""}\n'
        '{"url":"https://www.ems.com.cn/","success":false,"failure_reason":"HTTP 405"}\n',
        encoding="utf-8",
    )
    (parsed_dir / "policies.jsonl").write_text(
        '{"company":"顺丰速运","policy_categories":["服务条款","保价赔付"]}\n',
        encoding="utf-8",
    )

    report = build_crawl_report(tmp_path)

    assert "## 总览" in report
    assert "## 各来源政策记录数" in report
    assert "## 失败原因统计" in report
    assert "顺丰速运: 1" in report
    assert "HTTP 405: 1" in report
