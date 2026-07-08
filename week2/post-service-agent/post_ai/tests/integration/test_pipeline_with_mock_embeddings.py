from post_ai.schemas import PostalDocument
from post_ai.config import AppConfig
from post_ai.pipeline import build_and_save_faiss_from_old_h5, load_postal_documents
from post_ai.schemas import EmbeddingResult
from post_ai.vectorstores import FaissPostalIndex


def _fake_vector(text: str) -> list[float]:
    delivery_words = ["配送", "派送", "包裹", "站点", "快递"]
    refund_words = ["退款", "优惠券", "退回"]
    delivery = sum(word in text for word in delivery_words)
    refund = sum(word in text for word in refund_words)
    return [float(delivery), float(refund), 0.1]


def test_pipeline_shape_with_mock_embeddings() -> None:
    docs = [
        PostalDocument(
            split="train",
            index=0,
            session_id="s0",
            dialogue_id=0,
            source_path="train.json",
            content="用户咨询包裹派送到哪个站点，客服说明等待配送。",
            metadata={"intents": ["联系配送"]},
        ),
        PostalDocument(
            split="train",
            index=1,
            session_id="s1",
            dialogue_id=1,
            source_path="train.json",
            content="用户咨询优惠券取消订单后是否退回。",
            metadata={"intents": ["优惠券退回"]},
        ),
    ]
    index = FaissPostalIndex.build(
        documents=docs,
        vectors=[_fake_vector(doc.content) for doc in docs],
        embedding_model="mock",
        provider="mock",
    )

    hits = index.search(_fake_vector("我的包裹什么时候派送"), top_k=1)

    assert hits[0].document.session_id == "s0"


def test_real_data_to_faiss_pipeline_with_mock_embeddings() -> None:
    config = AppConfig.from_env()
    docs = load_postal_documents(config)[:50]
    index = FaissPostalIndex.build(
        documents=docs,
        vectors=[_fake_vector(doc.content) for doc in docs],
        embedding_model="mock",
        provider="mock",
    )

    hits = index.search(_fake_vector("包裹站点配送咨询"), top_k=3)

    assert len(hits) == 3
    assert all(hit.document.metadata["raw_filter_response"] == "true" for hit in hits)


def test_build_real_faiss_artifact_from_old_h5(tmp_path, monkeypatch) -> None:
    config = AppConfig.from_env()

    def fake_policy_embeddings(provider, texts, model):
        return EmbeddingResult(
            vectors=[[0.1] * 4096 for _ in texts],
            model=model,
            provider="mock-policy",
        )

    monkeypatch.setattr("post_ai.pipeline.embed_documents", fake_policy_embeddings)

    index = build_and_save_faiss_from_old_h5(artifact_dir=tmp_path, config=config)
    loaded = FaissPostalIndex.load(tmp_path)

    assert len(index.documents) == 6321 + 86
    assert len(loaded.documents) == 6321 + 86
    assert (tmp_path / "postal.faiss").stat().st_size > 0
    assert (tmp_path / "postal_metadata.json").stat().st_size > 0
    assert loaded.provider == "old-h5+mock-policy"
