"""导入邮政 RAG 数据的 Django 管理命令。

命令职责：
- 从 `post_ai` 数据加载逻辑读取筛选后的邮政对话切片；
- 写入 `PostalDocument`；
- 可选读取旧 H5 embedding，并写入 `PostalEmbedding` 的 pgvector 字段。

这个命令是数据入库入口，不负责模型生成，也不负责在线检索。
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models import PostalDocument, PostalEmbedding
from post_ai.config import AppConfig
from post_ai.old_embeddings import load_embedding_metadata, load_postal_vectors_from_h5
from post_ai.pipeline import load_postal_documents


class Command(BaseCommand):
    """`manage.py ingest_postal_rag` 命令实现。"""

    help = "Import postal-related CSDS dialogues into core_postaldocument."

    def add_arguments(self, parser) -> None:
        """注册命令行参数。

        `--limit` 方便冒烟测试；`--skip-embeddings` 方便只检查文档入库流程。
        """
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Import at most N documents. Useful for smoke tests.",
        )
        parser.add_argument(
            "--skip-embeddings",
            action="store_true",
            help="Only import PostalDocument rows; skip pgvector embedding rows.",
        )

    def handle(self, *args, **options) -> None:
        """执行导入流程。

        使用 `update_or_create` 保证命令可重复执行：同一来源文档再次导入会更新内容，
        而不是重复插入。embedding 与文档一对一，同样允许重复导入刷新向量。
        """
        config = AppConfig.from_env()
        documents = load_postal_documents(config)
        if options["limit"] is not None:
            documents = documents[: options["limit"]]

        vectors = None
        if not options["skip_embeddings"]:
            # H5 向量文件和 metadata 是历史产物；这里按文档来源 key 精确取对应向量，避免错位写入。
            metadata_by_split = load_embedding_metadata(config.data_paths.embedding_metadata_path)
            selected_keys = [
                (document.split, document.index, document.session_id, document.dialogue_id)
                for document in documents
            ]
            vectors = load_postal_vectors_from_h5(
                h5_path=config.data_paths.old_embedding_h5_path,
                metadata_by_split=metadata_by_split,
                selected_keys=selected_keys,
            )

        created = 0
        updated = 0
        embeddings_created = 0
        embeddings_updated = 0
        for offset, document in enumerate(documents):
            # 唯一键和 PostalDocument.Meta 里的 UniqueConstraint 保持一致。
            db_document, was_created = PostalDocument.objects.update_or_create(
                split=document.split,
                source_index=document.index,
                session_id=document.session_id,
                dialogue_id=document.dialogue_id,
                defaults={
                    "source_path": document.source_path,
                    "content": document.content,
                    "metadata": document.metadata,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            if vectors is not None:
                # pgvector 字段接收普通 Python list；numpy array 需要显式转 list。
                _, embedding_created = PostalEmbedding.objects.update_or_create(
                    document=db_document,
                    defaults={
                        "embedding": vectors[offset].tolist(),
                        "provider": "old-h5",
                        "model": "dialogue_embeddings.h5",
                    },
                )
                if embedding_created:
                    embeddings_created += 1
                else:
                    embeddings_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Imported postal RAG rows: "
                f"documents_created={created}, documents_updated={updated}, "
                f"embeddings_created={embeddings_created}, embeddings_updated={embeddings_updated}, "
                f"total={len(documents)}"
            )
        )
