# Project Tree

目标目录：

```text
/Users/bizi/Desktop/邮政实习/week2/post-service-agent/
├── README.md
├── manage.py
├── pyproject.toml
├── .env.example
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── post_ai/
│   ├── __init__.py
│   ├── config.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── ollama.py
│   │   ├── vllm.py
│   │   ├── openrouter.py
│   │   └── fastapi_provider.py
│   ├── embeddings.py
│   ├── source_loader.py
│   ├── filter_mapping.py
│   ├── retrieval.py
│   ├── prompts.py
│   ├── tickets.py
│   ├── schemas.py
│   └── tests/
│       ├── unit/
│       │   ├── test_ai_embeddings.py
│       │   ├── test_ai_filter_mapping.py
│       │   └── test_ai_ticket_schema.py
│       └── integration/
│           └── test_ai_pipeline.py
├── apps/
│   ├── __init__.py
│   ├── web/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── context_processors.py
│   │   └── templatetags/
│   │       ├── __init__.py
│   │       └── static_version.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── schemas.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       └── tickets.py
│   ├── conversations/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── migrations/
│   │       └── __init__.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py
│   │   │   ├── retrieval.py
│   │   │   └── source_mapping.py
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       └── ingest_postal_rag.py
│   │   └── migrations/
│   │       └── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── providers.py
│   │       ├── embedding.py
│   │       ├── chat.py
│   │       ├── titles.py
│   │       └── tickets.py
│   └── tickets/
│       ├── __init__.py
│       ├── apps.py
│       ├── admin.py
│       ├── models.py
│       ├── schemas.py
│       ├── services.py
│       └── migrations/
│           └── __init__.py
├── templates/
│   ├── base.html
│   └── web/
│       └── chat.html
├── static/
│   └── web/
│       ├── css/
│       │   └── chat.css
│       ├── js/
│       │   ├── chat.js
│       │   ├── markdown.js
│       │   └── sse.js
│       └── vendor/
│           └── README.md
├── tests/
│   ├── __init__.py
│   ├── test_rag_ingest.py
│   ├── test_retrieval.py
│   ├── test_ticket_json.py
│   └── test_api_chat.py
└── docs/
    ├── setup.md
    └── data_ingest.md
```

PRD 目录额外包含数据库迁移设计：

```text
/Users/bizi/Desktop/邮政实习/week2/prd/database_migration.md
```

## 目录说明

### `post_ai`

AI 工具包。先独立实现并测试通过，再被 Django apps 调用。

`post_ai/` 是一个可整体迁入 Django 项目的独立文件夹。AI 工具包自己的测试放在 `post_ai/tests/`，Django 项目测试放在项目级 `tests/`，两者分离。

职责：

- Ollama 调用。
- vLLM / OpenRouter / FastAPI provider 占位。
- SFT 如需本地权重，由独立 FastAPI 模型服务承载，本项目不直接用 Transformers 加载。
- embedding 前缀。
- CSDS 读取。
- `llm_filter` 映射。
- RAG prompt。
- 工单 JSON schema 和修复逻辑。

Django 不在 view 里直接写这些 AI 细节。

### `apps/web`

只负责 Web 页面，不写 RAG 业务逻辑。

### `apps/api`

只负责 django-ninja API 组织和 schema，不直接访问具体模型 provider 细节。

### `apps/rag`

负责数据导入、映射、向量存储、pgvector 检索。

### `apps/llm`

负责模型 provider 适配。所有模型名、prompt、stream 调用统一从这里走。

### `apps/tickets`

负责工单 JSON 的生成、校验和存储。

### `templates`

模板独立放在项目级 `templates`，页面由 `apps/web` 渲染。

### `static`

静态资源独立放在项目级 `static`。

CSS 和 JS 使用版本参数避免浏览器缓存。
