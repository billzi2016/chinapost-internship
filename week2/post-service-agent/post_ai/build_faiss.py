from __future__ import annotations

import argparse
from pathlib import Path

from post_ai.config import AppConfig
from post_ai.pipeline import build_and_save_faiss_from_old_h5


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS artifacts for postal RAG.")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to artifacts/faiss under project root.",
    )
    args = parser.parse_args()

    config = AppConfig.from_env()
    artifact_dir = (
        args.artifact_dir
        or config.vector_store_settings.faiss_artifact_dir
        or (config.artifact_dir / "faiss")
    )
    index = build_and_save_faiss_from_old_h5(artifact_dir=artifact_dir, config=config)
    print(f"FAISS index saved to: {artifact_dir}")
    print(f"Documents: {len(index.documents)}")
    print(f"Provider: {index.provider}")
    print(f"Embedding model: {index.embedding_model}")


if __name__ == "__main__":
    main()
