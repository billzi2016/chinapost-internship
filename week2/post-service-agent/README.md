# Post Service Agent

邮政客服智能助手。项目使用 Django + django-ninja + SSE 做 Web/API，使用 Ollama 调用本地模型，使用 PostgreSQL + pgvector 存储和检索邮政相关 RAG 数据。

## Quickstart

```bash
cd .
cp .env.example .env
docker compose up -d postgres
PYTHONPATH=. /opt/anaconda3/bin/python manage.py migrate
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:9999
```

打开：

```text
http://127.0.0.1:9999/
```

Swagger / OpenAPI 文档：

```text
http://127.0.0.1:9999/api/docs
```

如果端口被占用：

```bash
lsof -nP -iTCP:9999 -sTCP:LISTEN
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:10000
```

如果已经完成迁移和数据导入，也可以用 tmux 脚本启动 PostgreSQL、Ollama、Django：

```bash
./start_services.sh
```

## Tech Stack

- Python 3.13，当前使用 Anaconda base：`/opt/anaconda3/bin/python`
- Django
- django-ninja
- Django templates
- Server-Sent Events
- PostgreSQL
- pgvector + `pgvector.django`
- Ollama
- `gpt-oss:20B`
- `qwen3-embedding:8b`
- FAISS local fallback
- Bootstrap CSS
- 原生 JavaScript
- DOMPurify

## Architecture

```text
templates/web/chat.html
        |
        v
apps/web        Django template 页面
apps/api        django-ninja API + SSE 编排
apps/core       Django ORM models
post_ai         AI provider / RAG / prompt / ticket JSON / vector store
PostgreSQL      会话、消息、工单、RAG 文档、pgvector embedding
Ollama          chat model 和 embedding model
```

核心原则：

- Django 负责 Web、API、ORM、业务持久化。
- `post_ai` 负责模型 provider、RAG、prompt、工单 JSON。
- 模型调用走 provider，不在业务代码里写死 Ollama/vLLM/OpenRouter/FastAPI。
- 向量库走 provider，`microservice` 默认 pgvector，`local` 可用 FAISS fallback。

## Current Data

当前正式链路是 PostgreSQL + pgvector。

RAG 数据由两部分组成：

```text
CSDS 邮政对话切片: 6321
week1 政策/FAQ JSONL: 86
合计: 6407
```

week1 政策/FAQ 数据通过 symlink 接入 week2：

```text
week2/data/dataset.jsonl -> ../../week1-module-Web-Crawler/final-result/dataset.jsonl
```

旧 CSDS embedding 来源是已有文件：

```text
week2/data/embeddings/dialogue_embeddings.h5
week2/data/embeddings/dialogue_metadata.json
```

新 policy/FAQ embedding 离线生成到：

```text
week2/data/embeddings/policy_embeddings.h5
week2/data/embeddings/policy_metadata.json
```

生成旧 CSDS 对话 embedding：

```bash
cd ../data/embedding_pipeline
python dialogue_embedding_store.py
```

生成新 policy/FAQ embedding：

```bash
cd ../data/embedding_pipeline
python policy_embedding_store.py
```

说明：旧 CSDS embedding 已经存在，通常不要重跑；新 `dataset.jsonl` 更新后，只需要重新生成
`policy_embeddings.h5` 和 `policy_metadata.json`。

重新导入 pgvector：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
```

重新生成 FAISS artifact：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```

说明：旧 CSDS 数据继续使用历史 H5 向量；`dataset.jsonl` 不写入旧 H5，而是单独使用
`policy_embeddings.h5`。Django 导入和 FAISS 构建只读取已有 H5，不负责现场生成 embedding。

如果 `week1-module-Web-Crawler/final-result/dataset.jsonl` 更新了，或者首次把 symlink 接入
week2 后，需要先生成 policy embedding，再让新增数据真正进入检索链路：

```bash
cd ../data/embedding_pipeline
python policy_embedding_store.py

cd ../../post-service-agent
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```

第一条会写入/更新 PostgreSQL + pgvector 中的 `PostalDocument` 和 `PostalEmbedding`；
第二条会重新生成本地 FAISS artifact。只创建 symlink 不会自动更新 policy H5、数据库或 FAISS 文件。

## RAG Trigger Rules

聊天接口里的 RAG 开关只决定是否检索知识库；真正检索多少条，由
`apps/api/services.py` 中的 `_select_rag_profile()` 决定。

当前规则分两档：

| Profile | 触发条件 | top_k | 用途 |
| --- | --- | ---: | --- |
| `light` | 打开 RAG 且没有命中 strong 关键词 | 3 | 普通咨询、状态说明、一般业务问答 |
| `strong` | 打开 RAG 且命中高规则/高风险关键词 | 6 | 清关、赔付、禁限寄、资费、时效、证明材料等需要更多依据的问题 |
| `none` | 关闭 RAG | 0 | 不检索知识库，直接走模型回答 |

Strong RAG 当前使用可解释的关键词包含匹配，不是独立分类模型。命中以下任一词时，
本轮回答会把 `rag_profile` 设为 `strong`，并向向量库召回 6 条结果：

```text
清关、报关、海关、赔付、赔偿、理赔、投诉、申诉、改单、
禁寄、限寄、限制品、危险品、资费、费用、时限、时效、
超时、延误、材料、证明、依据、条款、规则、官方、
能不能寄、是否可以、需要准备、多久能
```

接口会在 SSE `meta` 事件和助手消息 `metadata` 中记录本次实际策略：

```json
{
  "use_rag": true,
  "use_sft": false,
  "rag_profile": "strong",
  "rag_top_k": 6
}
```

维护约定：如果后续要把关键词规则升级成 query classifier，优先替换
`_select_rag_profile()`，不要把触发逻辑散落到路由、前端或 prompt 里。

## Features

- 左侧历史会话
- 会话置顶和删除
- RAG 开关
- SFT 开关和不可用提示
- SSE 流式回答
- 引用对话展示
- Markdown 渲染和净化
- 修改上一条问题
- 重新回答上一条问题
- 手动生成工单
- 工单 JSON 首次生成后锁定
- 工单 JSON 复制和下载
- Provider health 展示

## Ticket JSON

工单会优先由 AI 生成严格 JSON，失败后使用规则兜底。

`user_id` 会被后端强制写成可回查数据库的标识：

```json
{
  "user_id": "conversation:123"
}
```

其中 `123` 对应 `Conversation.id`。

## Security

当前已经加入的安全边界：

- CSRF：所有写接口使用 Django CSRF 校验。
- XSS：Django template autoescape，前端 Markdown 使用 DOMPurify 净化。
- SQL 注入：业务数据、RAG 文档、embedding、pgvector 查询基本走 Django ORM / `pgvector.django`，当前代码路径不拼接用户输入到 SQL。
- 配置隔离：`.env` 不提交，`.env.example` 提供模板。
- `DEBUG=True` 仅用于当前开发阶段，上线前必须改成 `DJANGO_DEBUG=0`。

详细说明见：

```text
docs/security.md
```

## Tests

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m pytest post_ai/tests/unit -q
DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=. /opt/anaconda3/bin/python -m pytest tests/django/test_django_app.py -q
PYTHONPATH=. /opt/anaconda3/bin/python manage.py check
```

## Docs

- `docs/QUICKSTART.md`：启动、迁移、导入数据。
- `docs/RUNBOOK.md`：端口、PostgreSQL、Docker、tmux、故障排查。
- `docs/settings-configs.md`：配置分层。
- `docs/security.md`：安全边界。
- `docs/prd_v1/`：第一版 PRD、计划和任务清单。
