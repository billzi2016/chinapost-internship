# Post Service Agent

正式 Django 项目的目标目录。

当前阶段先实现独立 AI 工具包 `post_ai`，使用 FAISS 跑通 RAG 主链路。后续接入 Django 时，`post_ai` 作为一个完整文件夹整体迁入 Django 项目，Django apps 只调用 `post_ai`，不在 view/API 层直接写模型、数据映射或检索细节。

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

## 分离原则

- AI 工具包代码和 AI 测试都放在 `post_ai/` 内。
- Django 后续会有自己的 apps 和测试目录。
- 不把 Django 测试和 AI 工具包测试混在一起。
- `post_ai/` 后续可以整体移动进 Django 项目。

## 运行测试

```bash
PYTHONPATH=. pytest -p no:cacheprovider post_ai/tests/unit post_ai/tests/integration
```
