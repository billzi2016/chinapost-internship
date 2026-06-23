from __future__ import annotations

from django.db import migrations


def create_vector_index(apps, schema_editor) -> None:
    # The current imported H5 vectors are 4096-dimensional. pgvector ivfflat
    # indexes support up to 2000 dimensions for vector columns, so keep exact
    # search for now. The provider SQL still uses pgvector's <=> operator.
    return


def drop_vector_index(apps, schema_editor) -> None:
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_postalembedding"),
    ]

    operations = [
        migrations.RunPython(create_vector_index, drop_vector_index),
    ]
