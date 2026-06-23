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

- embedding 来源：`week2/data/embeddings/dialogue_embeddings.h5`
- metadata 来源：`week2/data/embeddings/dialogue_metadata.json`
- provider 标记：`old-h5`
- 文档数：6321

FAISS 作为 vector provider 封装在 `post_ai/vectorstores/faiss_store.py`。后续接入 Django + pgvector 时，保留 RAG 上层接口，把 `config/post_ai.yaml` 的 `vector_store.provider` 从 `faiss` 切到 `pgvector`，再实现 `post_ai/vectorstores/pgvector_store.py` 即可。

当前状态要实事求是：

- `faiss` provider 可用。
- `pgvector` provider 只是占位，尚未实现真实数据库检索。
- 当前 FAISS artifact 使用旧 `dialogue_embeddings.h5` 的文档向量。
- 旧 H5 没有用户 query embedding；Django 里的 RAG 请求目前是接线验证，不是最终语义检索效果。
- 真正查询语义检索需要接入 `qwen3-embedding:8b` query embedding 后再搜索 FAISS 或 pgvector。

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
