from post_ai.retrieval import FaissPostalIndex
from post_ai.schemas import PostalDocument


def _doc(index: int, content: str) -> PostalDocument:
    return PostalDocument(
        split="train",
        index=index,
        session_id=f"s{index}",
        dialogue_id=index,
        source_path="train.json",
        content=content,
        metadata={},
    )


def test_faiss_index_returns_nearest_document() -> None:
    docs = [_doc(0, "包裹派送"), _doc(1, "优惠券退回")]
    index = FaissPostalIndex.build(
        documents=docs,
        vectors=[[1.0, 0.0], [0.0, 1.0]],
        embedding_model="fake",
        provider="mock",
    )

    hits = index.search([0.9, 0.1], top_k=1)

    assert len(hits) == 1
    assert hits[0].document.content == "包裹派送"
    assert hits[0].rank == 1


def test_faiss_index_save_and_load_roundtrip(tmp_path) -> None:
    docs = [_doc(0, "包裹派送")]
    index = FaissPostalIndex.build(
        documents=docs,
        vectors=[[1.0, 0.0]],
        embedding_model="fake",
        provider="mock",
    )

    index.save(tmp_path)
    loaded = FaissPostalIndex.load(tmp_path)

    assert loaded.documents[0].source_key == docs[0].source_key
    assert loaded.search([1.0, 0.0], top_k=1)[0].score > 0.99
