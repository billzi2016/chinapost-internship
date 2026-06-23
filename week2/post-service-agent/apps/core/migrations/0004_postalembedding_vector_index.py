from __future__ import annotations

from django.db import migrations


def create_vector_index(apps, schema_editor) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS core_postalembedding_embedding_ivfflat "
        "ON core_postalembedding USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100);"
    )


def drop_vector_index(apps, schema_editor) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS core_postalembedding_embedding_ivfflat;")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_postalembedding"),
    ]

    operations = [
        migrations.RunPython(create_vector_index, drop_vector_index),
    ]
