"""为会话增加置顶能力的迁移。"""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """新增 `Conversation.is_pinned`，并调整默认排序。"""

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name="conversation",
            options={"ordering": ["-is_pinned", "-updated_at"]},
        ),
    ]
