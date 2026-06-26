"""生成抓取汇总报告。

报告是展示抓取结果最直接的方式之一，因此单独拆成模块，避免和调度逻辑耦合。
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """读取 JSONL 文件，不存在时返回空列表。"""

    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
    return records


def build_crawl_report(data_dir: Path) -> str:
    """根据日志和解析结果构建 Markdown 报告。"""

    logs_dir = data_dir / "logs"
    parsed_dir = data_dir / "parsed"
    fetch_results = _read_jsonl(logs_dir / "fetch_results.jsonl")
    policy_records = _read_jsonl(parsed_dir / "policies.jsonl")

    total_fetches = len(fetch_results)
    total_policies = len(policy_records)
    success_fetches = sum(1 for item in fetch_results if item.get("success") is True)
    skipped_or_failed = total_fetches - success_fetches

    company_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    failure_counter: Counter[str] = Counter()
    company_policy_counter: defaultdict[str, int] = defaultdict(int)

    for item in fetch_results:
        company_name = _guess_company_from_url(str(item.get("url", "")))
        company_counter[company_name] += 1
        failure_reason = str(item.get("failure_reason", "")).strip()
        if failure_reason:
            failure_counter[failure_reason] += 1

    for item in policy_records:
        company = str(item.get("company", "未知来源"))
        company_policy_counter[company] += 1
        for category in item.get("policy_categories", []):
            category_counter[str(category)] += 1

    lines = [
        "# Crawl Report",
        "",
        "## 总览",
        "",
        f"- 抓取请求总数: {total_fetches}",
        f"- 成功抓取数: {success_fetches}",
        f"- 跳过或失败数: {skipped_or_failed}",
        f"- 结构化政策记录数: {total_policies}",
        "",
        "## 各来源政策记录数",
        "",
    ]

    for company, count in sorted(company_policy_counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {company}: {count}")

    lines.extend(["", "## 主题分布", ""])
    for category, count in sorted(category_counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {category}: {count}")

    lines.extend(["", "## 失败原因统计", ""])
    if failure_counter:
        for reason, count in sorted(failure_counter.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- 无")

    return "\n".join(lines) + "\n"


def write_crawl_report(data_dir: Path) -> Path:
    """生成并写出抓取报告。"""

    report_path = data_dir / "logs" / "crawl_report.md"
    report_path.write_text(build_crawl_report(data_dir), encoding="utf-8")
    return report_path


def _guess_company_from_url(url: str) -> str:
    """根据 URL 粗略推断来源名称，用于失败统计。"""

    if "ems.com.cn" in url:
        return "中国邮政 EMS"
    if "sf-express.com" in url:
        return "顺丰速运"
    if "spb.gov.cn" in url:
        return "国家邮政局"
    if "ups.com" in url:
        return "UPS"
    if "fedex.com" in url:
        return "FedEx"
    if "dhl.com" in url:
        return "DHL Express"
    if "chinapost.com.cn" in url:
        return "中国邮政"
    if "jdl.com" in url:
        return "京东物流"
    if "yto.net.cn" in url:
        return "圆通速递"
    if "sto.cn" in url:
        return "申通快递"
    if "zto.com" in url:
        return "中通快递"
    if "yundaex.com" in url:
        return "韵达速递"
    if "jtexpress.com.cn" in url:
        return "极兔速递"
    if "deppon.com" in url:
        return "德邦快递"
    if "ky-express.com" in url:
        return "跨越速运"
    if "cainiao.com" in url:
        return "菜鸟"
    domain = urlparse(url).netloc
    return domain or "其他来源"
