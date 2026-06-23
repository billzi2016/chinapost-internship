import pytest

from post_ai.tickets import TicketJSONError, build_rule_based_ticket, parse_ticket_json


def test_parse_ticket_json_accepts_strict_payload() -> None:
    ticket = parse_ticket_json(
        """
        {
          "user_id": "u1",
          "timestamp": "2026-06-22T00:00:00Z",
          "service_type": "邮政客服",
          "issue_type": "配送咨询",
          "user_request": "查询派送时间",
          "summary": "用户咨询包裹派送时间。",
          "resolution": "建议等待派送通知。",
          "need_follow_up": false
        }
        """
    )

    assert ticket.issue_type == "配送咨询"
    assert ticket.need_follow_up is False


def test_parse_ticket_json_rejects_extra_fields() -> None:
    with pytest.raises(TicketJSONError):
        parse_ticket_json(
            """
            {
              "user_id": "",
              "timestamp": "2026-06-22T00:00:00Z",
              "service_type": "",
              "issue_type": "",
              "user_request": "",
              "summary": "",
              "resolution": "",
              "need_follow_up": false,
              "extra": "not allowed"
            }
            """
        )


def test_rule_based_ticket_has_required_fields() -> None:
    ticket = build_rule_based_ticket(user_request="查快递", summary="用户查询快递进度")

    assert ticket.service_type == "邮政客服"
    assert ticket.user_request == "查快递"
