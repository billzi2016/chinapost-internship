# Week 4：RAG 数据接入与检索增强

本周目标是把前期爬虫、筛选和结构化结果稳定接入问答系统，让 RAG 不只是“有开关”，而是能真正检索到可引用、可追溯、可维护的数据。

## 主要工作

- 梳理 `week1-module-Web-Crawler/final-result/dataset.jsonl` 的政策/FAQ 数据结构。
- 在 `week2/data/dataset.jsonl` 建立 symlink，避免重复复制同一份数据。
- 将 CSDS 邮政对话切片和 week1 政策/FAQ 数据统一映射为 `PostalDocument`。
- 保留旧 CSDS 的历史 H5 embedding，同时为新增 JSONL 政策数据单独生成 `policy_embeddings.h5`。
- 让新增数据同时进入 PostgreSQL + pgvector 和 FAISS fallback 两条检索链路。
- 在 README 中记录 RAG 数据来源、导入命令、FAISS 重建命令和 strong/light RAG 触发规则。

## 当前产物

- `week2/data/dataset.jsonl`：指向 week1 最终 JSONL 数据集的 symlink。
- `week2/post-service-agent/post_ai/source_loader.py`：新增 policy JSONL 加载与映射逻辑。
- `week2/post-service-agent/post_ai/pipeline.py`：统一加载 CSDS 与 policy 文档，并支持 FAISS 合并索引。
- `week2/post-service-agent/apps/core/management/commands/ingest_postal_rag.py`：支持把 policy 文档写入 pgvector。
- `week2/post-service-agent/README.md`：补充数据接入和 RAG 触发说明。

## 验证方式

```bash
cd ../week2/post-service-agent
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /opt/anaconda3/bin/python -m pytest -p no:cacheprovider post_ai/tests/integration/test_real_data_mapping.py post_ai/tests/integration/test_pipeline_with_mock_embeddings.py -q
PYTHONDONTWRITEBYTECODE=1 DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=. /opt/anaconda3/bin/python -m pytest -p no:cacheprovider tests/django/test_django_app.py::DjangoSmokeTests::test_ingest_postal_rag_is_idempotent_with_limit -q
```

## 后续注意

如果 `week1-module-Web-Crawler/final-result/dataset.jsonl` 更新，需要重新执行：

```bash
cd ../week2/data/embedding_pipeline
python policy_embedding_store.py

cd ../../post-service-agent
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```
