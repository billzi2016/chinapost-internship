from post_ai.embeddings import build_document_embedding_input, build_query_embedding_input


def test_query_embedding_input_uses_qwen3_instruction_prefix() -> None:
    text = build_query_embedding_input("我的快递什么时候派送")

    assert text.startswith("Instruct: Given a Chinese postal customer-service query")
    assert "\nQuery:我的快递什么时候派送" in text


def test_document_embedding_input_has_no_instruction_prefix() -> None:
    text = "用户询问包裹派送时间。客服回复请等待配送。"

    assert build_document_embedding_input(text) == text
