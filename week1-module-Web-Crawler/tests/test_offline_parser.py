"""测试离线 parse/filter 流程。"""

from datetime import datetime
import json

from crawler.models import FetchResult, SourceConfig
from crawler.offline_parser import parse_stored_fetches
from crawler.storage import Storage


def test_parse_stored_fetches_uses_raw_faq_json(tmp_path) -> None:
    """离线解析应从 raw 文件生成 policy 样本，不需要重新访问网络。"""

    storage = Storage(tmp_path)
    storage.ensure_directories()
    source = SourceConfig(
        source_id="ems_policy_network",
        company="中国邮政 EMS",
        source_type="官方服务网络",
        country_region="中国",
        base_url="https://www.ems.com.cn",
        entry_urls=[],
        allowed_topics=["产品服务", "时限标准"],
    )
    payload = {
        "code": 0,
        "data": [
            {
                "name": "热点",
                "faqList": [
                    {
                        "id": "keep",
                        "question": "即日专递产品介绍",
                        "answer": "即日专递业务面向所有用户开办，在特定线路提供当日上午寄件、当日送达的寄递服务。",
                    }
                ],
            }
        ],
    }
    result = FetchResult(
        url="http://nmc.ems.com.cn:9096/imcloud/commonFAQ/getListByChannel",
        status_code=200,
        content_type="application/json",
        text=json.dumps(payload, ensure_ascii=False),
        final_url="http://nmc.ems.com.cn:9096/imcloud/commonFAQ/getListByChannel",
        fetched_at=datetime.utcnow(),
        success=True,
        body_bytes=b"",
    )
    storage.append_fetch_result(
        result,
        source_id=source.source_id,
        company=source.company,
        parser_kind="faq_json",
    )

    policy_count, filtered_count = parse_stored_fetches([source], storage)

    assert policy_count == 1
    assert filtered_count == 0
    assert (tmp_path / "parsed" / "policies.jsonl").exists()


def test_parse_stored_fetches_does_not_clear_outputs_when_nothing_parseable(tmp_path) -> None:
    """旧格式或不可解析日志不应清空已有 parsed 输出。"""

    storage = Storage(tmp_path)
    storage.ensure_directories()
    policies_path = tmp_path / "parsed" / "policies.jsonl"
    policies_path.write_text('{"title":"existing"}\n', encoding="utf-8")
    (tmp_path / "logs" / "fetch_results.jsonl").write_text(
        '{"url":"https://example.com","success":true,"text":"short"}\n',
        encoding="utf-8",
    )

    policy_count, filtered_count = parse_stored_fetches([], storage)

    assert policy_count == 0
    assert filtered_count == 0
    assert policies_path.read_text(encoding="utf-8") == '{"title":"existing"}\n'
