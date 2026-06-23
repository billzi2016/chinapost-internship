from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models

import pgvector.django.vector


def create_pgvector_extension(apps, schema_editor) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector;")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_conversation_is_pinned"),
    ]

    operations = [
        migrations.RunPython(create_pgvector_extension, migrations.RunPython.noop),
        migrations.CreateModel(
            name="PostalEmbedding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("embedding", pgvector.django.vector.VectorField(dimensions=4096)),
                ("provider", models.CharField(max_length=64)),
                ("model", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "document",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embedding",
                        to="core.postaldocument",
                    ),
                ),
            ],
        ),
    ]
