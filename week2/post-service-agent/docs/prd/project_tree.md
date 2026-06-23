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
│   ├── vectorstores/
│   │   ├── __init__.py
│   │   └── faiss_store.py
│   ├── old_embeddings.py
│   ├── build_faiss.py
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
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   └── migrations/
│   │       ├── __init__.py
│   │       └── 0001_initial.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── urls.py
│   └── web/
│       ├── __init__.py
│       ├── apps.py
│       ├── urls.py
│       ├── views.py
│       └── context_processors.py
├── templates/
│   ├── base.html
│   └── web/
│       └── chat.html
├── static/
│   └── web/
│       ├── css/
│       │   └── chat.css
│       ├── js/
│       │   └── chat.js
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
- 当前阶段 FAISS vector store。
- 使用已有 `dialogue_embeddings.h5` 构建 `artifacts/faiss/postal.faiss`。

Django 不在 view 里直接写这些 AI 细节。

FAISS 只作为临时 vector store 层存在。后续切换 pgvector 时，不改 provider、数据映射、prompt、ticket 等上层逻辑，只替换 `post_ai/vectorstores` 对应实现。

### `apps/core`

Django ORM 层。当前 KISS 结构下，会话、消息、邮政文档、引用和工单都放在这里。

### `apps/api`

django-ninja API 和 SSE 层。只做 HTTP 编排，调用 `post_ai` 和 `apps/core`，不重新实现 AI provider。

### `apps/web`

Django templates 页面层。只负责页面渲染和静态资源入口，不写 RAG 业务逻辑。

### `templates`

模板独立放在项目级 `templates`，页面由 `apps/web` 渲染。

### `static`

静态资源独立放在项目级 `static`。

CSS 和 JS 使用版本参数避免浏览器缓存。
