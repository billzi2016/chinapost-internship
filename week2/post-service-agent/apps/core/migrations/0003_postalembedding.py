"""新增 pgvector embedding 表的迁移。"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models

import pgvector.django.vector


def create_pgvector_extension(apps, schema_editor) -> None:
    """PostgreSQL 环境下确保 vector 扩展存在；SQLite 测试环境直接跳过。"""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector;")


class Migration(migrations.Migration):
    """创建 `PostalEmbedding`，与 `PostalDocument` 一对一绑定。"""

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
