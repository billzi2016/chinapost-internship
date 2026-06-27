"""测试官方客服知识库 FAQ JSON 解析。"""

import json

from crawler.faq_parser import parse_faq_json
from crawler.models import SourceConfig


def test_parse_faq_json_keeps_policy_like_answers() -> None:
    """真实 FAQ 答案应转成训练样本，跳转机器人应跳过。"""

    source = SourceConfig(
        source_id="ems_policy_network",
        company="中国邮政 EMS",
        source_type="官方服务网络",
        country_region="中国",
        base_url="https://www.ems.com.cn",
        entry_urls=[],
        allowed_topics=["产品服务", "时限标准", "服务条款"],
    )
    payload = {
        "code": 0,
        "data": [
            {
                "name": "热点",
                "faqList": [
                    {
                        "id": "skip",
                        "question": "我要寄件",
                        "answer": "跳转机器人",
                    },
                    {
                        "id": "keep",
                        "question": "即日专递产品介绍",
                        "answer": "&nbsp;即日专递业务面向所有用户开办，在特定线路提供当日上午寄件、当日送达的寄递服务。",
                    },
                ],
            }
        ],
    }

    records, filtered = parse_faq_json(
        source,
        "http://nmc.ems.com.cn:9096/imcloud/commonFAQ/getListByChannel",
        json.dumps(payload, ensure_ascii=False),
    )

    assert len(records) == 1
    assert records[0].title == "即日专递产品介绍"
    assert "产品服务" in records[0].policy_categories
    assert filtered == []
