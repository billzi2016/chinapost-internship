from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "用户"), ("assistant", "助手"), ("system", "系统")], max_length=32)),
                ("content", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="core.conversation")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="PostalDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("split", models.CharField(max_length=16)),
                ("source_index", models.IntegerField()),
                ("session_id", models.CharField(max_length=128)),
                ("dialogue_id", models.IntegerField()),
                ("source_path", models.TextField()),
                ("content", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Citation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.FloatField()),
                ("quoted_text", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="citations", to="core.postaldocument")),
                ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="citations", to="core.message")),
            ],
        ),
        migrations.CreateModel(
            name="Ticket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payload", models.JSONField(default=dict)),
                ("is_valid", models.BooleanField(default=False)),
                ("validation_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tickets", to="core.conversation")),
                ("message", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tickets", to="core.message")),
            ],
        ),
        migrations.AddConstraint(
            model_name="postaldocument",
            constraint=models.UniqueConstraint(fields=("split", "source_index", "session_id", "dialogue_id"), name="uniq_postal_document_source"),
        ),
    ]
