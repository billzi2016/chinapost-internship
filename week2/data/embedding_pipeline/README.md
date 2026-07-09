# Embedding Pipeline

这个目录放离线 embedding 生成脚本。这里的脚本只负责把数据编码成 HDF5 和 metadata 文件，不连接 Django，也不写 PostgreSQL。

## 为什么放在这里

- embedding 生成耗时长，应该作为离线数据准备步骤。
- Django 的 `ingest_postal_rag` 只负责读取已有文档和已有向量并写库。
- 旧 CSDS embedding 和新 policy/FAQ embedding 分开存放，避免破坏原始 H5 的 `train/val/test` 对齐关系。

## 输出文件

旧 CSDS 对话 embedding：

```text
week2/data/embeddings/dialogue_embeddings.h5
week2/data/embeddings/dialogue_metadata.json
```

新 policy/FAQ embedding：

```text
week2/data/embeddings/policy_embeddings.h5
week2/data/embeddings/policy_metadata.json
```

## 生成旧 CSDS 对话 embedding

这份逻辑从 `week1/第一版/filter/embedding_store.py` copy 过来，用于保留历史可复现入口。通常不需要重新运行，因为旧文件已经存在。

```bash
cd week2/data/embedding_pipeline
python dialogue_embedding_store.py
```

## 生成新 policy/FAQ embedding

首次接入或 `week2/data/dataset.jsonl` 更新后运行：

```bash
cd week2/data/embedding_pipeline
python policy_embedding_store.py
```

生成完后再进入 Django 项目刷新 pgvector 和 FAISS：

```bash
cd ../../post-service-agent
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```

## 可配置环境变量

- `OLLAMA_URL`：默认 `http://127.0.0.1:11434`
- `EMBED_MODEL`：默认 `qwen3-embedding:8b`
- `EMBED_BATCH_SIZE`：默认 `8`
- `WRITE_BATCH_SIZE`：默认 `32`
- `EMBED_SLEEP_SECONDS`：默认 `0.5`

## 断点续跑

HDF5 dataset 会记录 `completed` 属性。脚本中断后重新运行，会从已完成位置继续写，不会重算前面已经写入的向量。
