# Post Service Agent

邮政客服智能助手。项目使用 Django + django-ninja + SSE 做 Web/API，使用 Ollama 调用本地模型，使用 PostgreSQL + pgvector 存储和检索邮政相关 RAG 数据。

## Quickstart

```bash
cd /Users/bizi/Desktop/邮政实习/week2/post-service-agent
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

RAG 数据已经全量导入：

```text
PostalDocument: 6321
PostalEmbedding: 6321
```

embedding 来源是已有文件：

```text
week2/data/embeddings/dialogue_embeddings.h5
week2/data/embeddings/dialogue_metadata.json
```

导入命令：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
```

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
