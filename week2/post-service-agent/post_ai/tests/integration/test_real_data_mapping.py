from post_ai.config import AppConfig
from post_ai.filter_mapping import iter_postal_documents, load_filter_results
from post_ai.source_loader import load_all_csds


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
