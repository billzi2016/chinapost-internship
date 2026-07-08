from post_ai.config import AppConfig
from post_ai.filter_mapping import iter_postal_documents, load_filter_results
from post_ai.pipeline import load_postal_documents
from post_ai.source_loader import load_all_csds, load_policy_jsonl


def test_real_data_filter_mapping_counts() -> None:
    config = AppConfig.from_env()
    csds = load_all_csds(config.data_paths.csds_dir)
    filters = load_filter_results(config.data_paths.filter_path)

    docs = list(iter_postal_documents(csds, filters, config.data_paths.csds_dir))

    assert len(csds["train"]) == 9101
    assert len(csds["val"]) == 800
    assert len(csds["test"]) == 800
    assert len(docs) == 6321
    assert docs[0].metadata["split"] == "train"
    assert docs[0].metadata["raw_filter_response"] == "true"


def test_policy_jsonl_symlink_is_loaded_as_rag_documents() -> None:
    config = AppConfig.from_env()

    policy_docs = load_policy_jsonl(config.data_paths.policy_dataset_jsonl_path)
    all_docs = load_postal_documents(config)

    assert config.data_paths.policy_dataset_jsonl_path.is_symlink()
    assert len(policy_docs) == 86
    assert len(all_docs) == 6321 + 86
    assert policy_docs[0].split == "policy"
    assert policy_docs[0].metadata["source_kind"] == "policy_jsonl"
    assert "即日专递产品介绍" in policy_docs[0].content
