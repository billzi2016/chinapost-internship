# filter

这个目录负责对 `CSDS` 做“对话级 embedding -> LLM 二分类过滤 -> 降维可视化”。

## 文件说明

- `dataloader.py`：读取数据并把一条完整对话拼成文本
- `embedding_store.py`：调用 `qwen3-embedding:8b`，按 request batch=`8` 编码，在内存中攒够 `32` 条后分块写入 `h5`
- `llm_filter.py`：调用 `gpt-oss:20b`，判断一条对话是否和快递/邮政相关，只接受 `true/false`
- `vis.py`：读取 embedding 和过滤结果，生成 `PCA / t-SNE / UMAP` 图
- `main.py`：统一入口，顺序调用三个阶段

## 输出目录

- `outputs/embeddings/dialogue_embeddings.h5`
- `outputs/embeddings/dialogue_metadata.json`
- `outputs/llm_filter/postal_filter_results.json`
- `outputs/vis/*.png`

## 设计口径

- embedding 粒度：单条完整对话
- `h5` 数据集：`train`、`val`、`test`
- 压缩：`compression="gzip"`，`compression_opts=1`
- HDF5 写入方式：固定 shape 的 dataset 按切片分块写入，并记录 `completed` 断点，可续跑且不重复重写前面已完成部分
- LLM 过滤粒度：单条完整对话
- LLM 过滤保存方式：读取已有 `postal_filter_results.json` 后从断点继续，每处理 `32` 条保存一次，避免中断后重复调用前面已完成的样本
- 可视化颜色：
  - 灰色：全部数据中的其他对话
  - 红色：被 LLM 判定为快递/邮政相关的对话

## 依赖与前提

- 本地需要可访问的 Ollama 服务
- 默认模型名：
  - embedding：`qwen3-embedding:8b`
  - filter：`gpt-oss:20b`
- 默认地址：`http://127.0.0.1:11434`
- `UMAP` 依赖 `umap-learn`；如果没装，脚本会跳过 `UMAP` 图
- 目录下自带一个 `.env`，脚本启动时会自动读取

## 可配置环境变量

- `OLLAMA_URL`
- `EMBED_MODEL`
- `EMBED_BATCH_SIZE`
- `WRITE_BATCH_SIZE`
- `FILTER_MODEL`
- `EMBED_PREFIX`

## 安装方式

```bash
cd .
pip install -r requirements.txt
```

## 关于 embedding 前缀

当前默认前缀采用 instruction-aware 形式：

```text
Instruct: Represent the following Chinese customer service dialogue for topic filtering, clustering, and semantic analysis.
Text:
```

这样做的原因是：

- Qwen3-Embedding-8B 官方模型卡明确说明它支持自定义 instruction
- 官方说明大多数下游任务里，使用 instruction 相比不用通常会提升约 `1%~5%`
- 官方还建议 instruction 尽量用英文

这里我做的是任务化改写：因为我们不是标准“query-doc 检索”，而是“整条对话的筛选、聚类、语义表示”，所以把任务目标写进统一前缀里，并对所有完整对话一致使用。脚本会优先读取同目录 `.env` 里的 `EMBED_PREFIX`，不会优先吃 Python 里的硬编码前缀。

## 运行方式

```bash
python main.py
```
