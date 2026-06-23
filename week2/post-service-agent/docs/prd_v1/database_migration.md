# Database Migration Plan

## 1. 数据库原则

本项目使用一个 PostgreSQL 数据库。

建议数据库名：

```text
post_service_agent
```

`pgvector` 不是单独数据库，而是 PostgreSQL 扩展。

因此：

- 不拆业务库和向量库。
- 不单独维护 vector database。
- 所有业务数据、RAG 文档、embedding、引用记录、工单 JSON 都在同一个 PostgreSQL 数据库中。
- 在该数据库内启用 `vector` extension。

初始化 SQL：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. 表设计概览

建议表：

```text
conversations_conversation
conversations_message
core_postaldocument
core_postalembedding
rag_citation
tickets_ticket
```

逻辑关系：

```text
Conversation 1 ── N Message
PostalDocument 1 ── 1 PostalEmbedding
Message 1 ── N Citation
PostalDocument 1 ── N Citation
Conversation 1 ── N Ticket
Message 1 ── N Ticket
```

## 3. pgvector 维度

当前默认 embedding 模型：

```text
qwen3-embedding:8b
```

历史 H5 文件中旧 embedding 维度是：

```text
4096
```

新系统如果使用 `qwen3-embedding:8b` 重新生成 embedding，需要以实际 provider 返回维度为准。

迁移策略：

- `PostalEmbedding.embedding` 的 vector 维度必须和当前 embedding 模型输出一致。
- 不要把旧 H5 embedding 和新模型 embedding 混在同一字段中。
- 如果未来更换 embedding 模型，应新增 embedding model 版本记录，必要时重新建索引或重新入库。

PRD 阶段建议先按 `4096` 规划，因为当前已有 H5 embedding 是 `(N, 4096)`。

实际开工时必须先用 provider 调一次 `qwen3-embedding:8b`，确认真实向量维度后再生成 migration。

## 4. Django Migration 示例

以下是后续项目中可参考的 migration 示例，不是当前已创建代码。

目标文件位置示例：

```text
post-service-agent/apps/core/migrations/0001_initial.py
```

示例：

```python
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="PostalDocument",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("source_dataset", models.CharField(max_length=32)),
                ("source_path", models.TextField()),
                ("split", models.CharField(max_length=16)),
                ("source_index", models.IntegerField()),
                ("source_conversation_id", models.CharField(max_length=128)),
                ("source_dialogue_id", models.IntegerField()),
                ("source_message_ids", models.JSONField(default=list)),
                ("content", models.TextField()),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.RunSQL(
            sql="""
            CREATE TABLE core_postalembedding (
                id bigserial PRIMARY KEY,
                document_id bigint NOT NULL UNIQUE
                    REFERENCES core_postaldocument(id)
                    ON DELETE CASCADE,
                embedding vector(4096) NOT NULL,
                embedding_model varchar(128) NOT NULL,
                provider varchar(64) NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS core_postalembedding;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE INDEX core_postalembedding_embedding_hnsw
            ON core_postalembedding
            USING hnsw (embedding vector_cosine_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS core_postalembedding_embedding_hnsw;",
        ),
    ]
```

## 5. Conversation Migration 示例

目标文件位置示例：

```text
post-service-agent/apps/core/migrations/0001_initial.py
```

示例：

```python
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=128, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("role", models.CharField(max_length=32)),
                ("content", models.TextField()),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="core.conversation",
                    ),
                ),
            ],
        ),
    ]
```

## 6. Citation Migration 示例

引用记录放在 `apps/core`。

示例：

```python
migrations.CreateModel(
    name="Citation",
    fields=[
        ("id", models.BigAutoField(primary_key=True, serialize=False)),
        ("score", models.FloatField()),
        ("quoted_text", models.TextField()),
        ("metadata", models.JSONField(default=dict)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        (
            "message",
            models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="citations",
                to="core.message",
            ),
        ),
        (
            "document",
            models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="citations",
                to="core.postaldocument",
            ),
        ),
    ],
)
```

## 7. Ticket Migration 示例

目标文件位置示例：

```text
post-service-agent/apps/core/migrations/0001_initial.py
```

示例：

```python
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ticket",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("payload", models.JSONField(default=dict)),
                ("is_valid", models.BooleanField(default=False)),
                ("validation_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="core.conversation",
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="tickets",
                        to="core.message",
                    ),
                ),
            ],
        ),
    ]
```

## 8. 索引策略

普通索引：

- `Conversation.updated_at`
- `Message.conversation_id`
- `Message.created_at`
- `PostalDocument.split`
- `PostalDocument.source_index`
- `PostalDocument.source_conversation_id`
- `PostalDocument.source_dialogue_id`
- `Citation.message_id`
- `Citation.document_id`
- `Ticket.conversation_id`

向量索引：

```sql
CREATE INDEX core_postalembedding_embedding_hnsw
ON core_postalembedding
USING hnsw (embedding vector_cosine_ops);
```

说明：

- 当前 RAG 检索默认使用 cosine 相似度。
- 如果 embedding provider 后续变化，需要重新评估距离函数和索引。

## 9. 数据导入关系

导入时写入顺序：

1. 读取 CSDS、llm_filter、metadata。
2. 校验 `split + index + session_id + dialogue_id`。
3. 只处理 `is_postal_related == true`。
4. 创建或更新 `PostalDocument`。
5. 调用 embedding provider。
6. 写入或更新 `PostalEmbedding`。

幂等键建议：

```text
split + source_index + source_conversation_id + source_dialogue_id
```

建议在 `PostalDocument` 上加唯一约束：

```text
UniqueConstraint(
    fields=[
        "split",
        "source_index",
        "source_conversation_id",
        "source_dialogue_id",
    ],
    name="uniq_postal_document_source",
)
```

## 10. 不能做的事

- 不拆成两个 PostgreSQL 数据库。
- 不引入独立向量数据库。
- 不把 false 的客服泛化数据写入 pgvector。
- 不把旧 H5 embedding 和新 embedding 混用。
- 不在 migration 里写死未来不可确认的模型服务地址。
- 不把 provider 密钥写入数据库 migration。
