# Post Service Agent

邮政客服智能助手 Django 项目。

当前结构遵循 KISS：

- `post_ai/`：完整 AI 工具包，包含 provider、RAG、FAISS vector store、数据映射、prompt、工单 JSON schema 和 AI 自己的测试。
- `apps/core/`：Django ORM 模型，包含会话、消息、邮政文档、引用、工单。
- `apps/api/`：django-ninja API 和 SSE。
- `apps/web/`：Django templates 页面和静态资源入口。

Django 只调用 `post_ai`，不拆散 `post_ai`，也不在 view/API 层直接写模型或检索细节。

## 技术栈

- Python 3.13，当前使用 Anaconda base：`/opt/anaconda3/bin/python`
- Django
- django-ninja
- Django templates
- 原生 JavaScript
- Bootstrap 兼容 CSS，本地 vendor 文件
- Markdown 渲染和 sanitizer，本地 vendor 文件
- FAISS，当前阶段的本地 vector store
- PostgreSQL + pgvector，后续正式数据库/vector store
- Ollama provider，当前默认 chat/embedding provider
- vLLM / OpenRouter / FastAPI provider，占位

## 配置

AI 工具包使用自己的 YAML 配置：

```text
config/post_ai.yaml
```

这个文件只属于 `post_ai`。Django 后续使用自己的 `settings.py` 和环境配置，不把 Django 的 Web、数据库、静态资源配置混进 `post_ai.yaml`。

配置项包括：

- chat provider
- embedding provider
- SFT provider
- vector store provider
- FAISS artifact 路径
- pgvector 占位配置

## 当前范围

- Provider 标准接口
- Ollama provider
- vLLM / OpenRouter / FastAPI provider 占位
- Qwen3 embedding query 前缀
- CSDS 数据读取
- `llm_filter` 到 CSDS 映射
- FAISS 向量检索
- RAG prompt
- 工单 JSON schema
- `post_ai/tests/unit` 单元测试
- `post_ai/tests/integration` 整体测试
- Django KISS app 骨架
- Django 页面/API/SSE 接线
- Django 测试

## FAISS Artifact

当前阶段用 FAISS 跑通 RAG，正式 artifact 位于：

```text
artifacts/faiss/postal.faiss
artifacts/faiss/postal_metadata.json
```

构建命令：

```bash
PYTHONPATH=. python -m post_ai.build_faiss
```

当前 artifact 使用已有数据：

- 旧 CSDS embedding 来源：`week2/data/embeddings/dialogue_embeddings.h5`
- 旧 CSDS metadata 来源：`week2/data/embeddings/dialogue_metadata.json`
- policy/FAQ embedding 来源：`week2/data/embeddings/policy_embeddings.h5`
- policy/FAQ metadata 来源：`week2/data/embeddings/policy_metadata.json`
- provider 标记：`old-h5+policy-h5`
- 文档数：6321 条 CSDS 对话切片 + 86 条 policy/FAQ

FAISS 和 pgvector 都作为 vector provider 封装在 `post_ai/vectorstores/`。当前通过 `config/post_ai.yaml` 的 `mode` 做总闸：`local` 默认走 FAISS，`microservice` 默认走 pgvector；`POST_AI_VECTOR_PROVIDER` 只用于临时覆盖。

当前状态要实事求是：

- `faiss` provider 可用。
- `pgvector` provider 可用，正式链路默认使用 PostgreSQL + pgvector，并通过 `pgvector.django` 接入 Django ORM。
- 当前 FAISS artifact 合并旧 `dialogue_embeddings.h5` 和新 `policy_embeddings.h5`。
- pgvector 数据由 Django ORM migration 建表，并通过 `ingest_postal_rag` 导入两个已有 H5。
- `policy_embeddings.h5` 由 `week2/data/embedding_pipeline/policy_embedding_store.py` 离线生成，不在 Django ingest 中现场生成。
- 查询时使用 `qwen3-embedding:8b` 生成 query embedding，再搜索当前 mode 选择的向量库。

## 分离原则

- AI 工具包代码和 AI 测试都放在 `post_ai/` 内。
- Django 后续会有自己的 apps 和测试目录。
- 不把 Django 测试和 AI 工具包测试混在一起。
- `post_ai/` 后续可以整体移动进 Django 项目。

## Quickstart

启动、端口冲突处理、FAISS artifact 生成和 Docker 说明见：

- [QUICKSTART.md](QUICKSTART.md)

## 运行测试

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m pytest -p no:cacheprovider post_ai/tests/unit post_ai/tests/integration
PYTHONPATH=. /opt/anaconda3/bin/python manage.py test tests.django
```
