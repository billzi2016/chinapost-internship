from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models import PostalDocument
from post_ai.config import AppConfig
from post_ai.pipeline import load_postal_documents


class Command(BaseCommand):
    help = "Import postal-related CSDS dialogues into core_postaldocument."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Import at most N documents. Useful for smoke tests.",
        )

    def handle(self, *args, **options) -> None:
        documents = load_postal_documents(AppConfig.from_env())
        if options["limit"] is not None:
            documents = documents[: options["limit"]]

        created = 0
        updated = 0
        for document in documents:
            _, was_created = PostalDocument.objects.update_or_create(
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported postal documents: created={created}, updated={updated}, total={len(documents)}"
            )
        )
