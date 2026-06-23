# Post Service Agent

正式 Django 项目的目标目录。

当前阶段先实现独立 AI 工具包 `post_ai`，使用 FAISS 跑通 RAG 主链路。后续接入 Django 时，`post_ai` 作为一个完整文件夹整体迁入 Django 项目，Django apps 只调用 `post_ai`，不在 view/API 层直接写模型、数据映射或检索细节。

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

## 分离原则

- AI 工具包代码和 AI 测试都放在 `post_ai/` 内。
- Django 后续会有自己的 apps 和测试目录。
- 不把 Django 测试和 AI 工具包测试混在一起。
- `post_ai/` 后续可以整体移动进 Django 项目。

## 运行测试

```bash
PYTHONPATH=. pytest -p no:cacheprovider post_ai/tests/unit post_ai/tests/integration
```
