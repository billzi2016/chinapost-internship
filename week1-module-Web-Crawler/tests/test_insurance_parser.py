"""测试保险、保价和理赔相关文本解析。"""

from crawler.insurance_parser import parse_insurance_terms


def test_parse_insurance_terms_extracts_core_fields() -> None:
    """应能从典型保价条款中抽取基础字段。"""

    text = (
        "本服务支持保价。最高赔偿1000元。用户应在签收后7日内提出索赔，"
        "并提交发票、签收证明及破损照片。易碎品和现金不在赔付范围内。"
    )

    result = parse_insurance_terms(text)

    assert result["insurance_available"] is True
    assert result["insurance_type"] == "保价"
    assert "最高赔偿1000元" in str(result["compensation_limit"])
    assert "7日内提出索赔" in str(result["claim_deadline"])
    assert "现金" in result["insurance_exclusions"]
    assert "易碎品" in result["insurance_exclusions"]
    assert "价值证明" in result["requirements"]
    assert "签收证明" in result["requirements"]
    assert "破损照片" in result["requirements"]


def test_parse_insurance_terms_skips_homepage_like_text() -> None:
    """首页导航词里的“保险”不应直接触发保险结构化字段。"""

    text = (
        "首页 个人服务 企业服务 国际服务 保险服务 立即下单 运单查询 "
        "网点查询 关于我们 联系我们 新闻中心"
    )

    result = parse_insurance_terms(text)

    assert result["insurance_available"] is False
    assert result["insurance_type"] == "未知"
