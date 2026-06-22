# AI Plan

## 1. 目标

基于已筛选的邮政相关数据建设 RAG：

- 从 `llm_filter` 中读取邮政相关筛选结果。
- 根据筛选结果映射原始 CSDS 对话。
- 丢弃非邮政系统相关的客服泛化信息。
- 使用 `qwen3-embedding:8b` 生成向量。
- 将邮政相关内容写入 PostgreSQL + pgvector。
- 查询时使用向量检索召回引用对话。
- 使用 `gpt-oss:20b` 生成回答、会话标题和工单信息。

## 2. 本地模型

### 2.1 生成模型

- 模型名：`gpt-oss:20b`
- 用途：
  - 主聊天回复
  - 会话标题总结
  - 工单自然语言总结
  - 工单 JSON 初稿生成

### 2.2 Embedding 模型

- 模型名：`qwen3-embedding:8b`
- 用途：
  - 入库阶段生成邮政相关对话向量
  - 查询阶段生成用户问题向量

### 2.3 Embedding 前缀

Qwen3-Embedding 官方模型卡说明：query 侧建议使用 instruction，document 侧不需要加 instruction。

本项目固定使用下面的 query 前缀格式：

```text
Instruct: Given a Chinese postal customer-service query, retrieve relevant postal-service dialogue passages that answer the query
Query:{query}
```

具体规则：

- 用户查询 embedding：必须加上述 `Instruct` + `Query` 前缀。
- 文档入库 embedding：不加 instruction，直接使用清洗后的邮政相关对话文本。
- instruction 使用英文，因为 Qwen 官方建议多语言场景下 instruction 优先使用英文。
- `Query:` 后面直接拼接用户问题，保持官方格式。

代码层建议：

```python
POSTAL_RETRIEVAL_INSTRUCTION = (
    "Given a Chinese postal customer-service query, "
    "retrieve relevant postal-service dialogue passages that answer the query"
)


def build_query_embedding_input(query: str) -> str:
    return f"Instruct: {POSTAL_RETRIEVAL_INSTRUCTION}\nQuery:{query}"


def build_document_embedding_input(text: str) -> str:
    return text
```

Ollama 调用 `qwen3-embedding:8b` 时，把上述最终字符串传给 `/api/embed` 或 Python SDK 的 `ollama.embed(input=...)`。

参考依据：

- Qwen/Qwen3-Embedding-8B 官方模型卡：query 使用 `Instruct: {task_description}\nQuery:{query}`，document 不需要 instruction。
- Ollama qwen3-embedding 模型页：通过 `/api/embed` 或 SDK `embed` 传入 `input`。

## 3. 数据路径

- 原始数据：`/Users/bizi/Desktop/邮政实习/week2/data/CSDS`
- 筛选结果：`/Users/bizi/Desktop/邮政实习/week2/data/llm_filter`
- 历史 embedding 输出：`/Users/bizi/Desktop/邮政实习/week2/data/embeddings`

详细文件格式见：

- `/Users/bizi/Desktop/邮政实习/week2/prd/data_format.md`

关键约束：

- `CSDS/train.json`、`CSDS/val.json`、`CSDS/test.json` 是真正原始数据。
- `CSDS/._*.json` 是 macOS AppleDouble 文件，必须跳过。
- `postal_filter_results.json` 顶层为 `train/val/test`。
- 每条 filter 记录通过 `index + session_id + dialogue_id` 映射 CSDS。
- 只有 `is_postal_related == true` 的对话允许进入 pgvector。
- `dialogue_embeddings.h5` 的 `train/val/test` dataset 和 metadata、CSDS、filter 通过同一个 index 对齐。
- 旧 H5 embedding 不能和新 `qwen3-embedding:8b` 生成的向量混用，除非明确记录模型来源和向量维度。

## 4. 数据处理流程

### 4.1 读取筛选结果

`llm_filter` 是筛选依据。

处理逻辑：

1. 遍历 `llm_filter`。
2. 识别哪些条目被判定为邮政相关。
3. 提取可映射回 CSDS 原始数据的标识。
4. 对无法映射的条目记录日志，不直接入库。

映射必须校验：

```text
CSDS item Session_id == filter session_id
CSDS item DialogueID == filter dialogue_id
filter index == CSDS array index
```

### 4.2 映射原始数据

从 `/Users/bizi/Desktop/邮政实习/week2/data/CSDS` 找到对应原始对话。

保留信息：

- 数据集来源
- 文件路径
- 原始会话 ID
- 原始消息 ID
- 角色
- 原始文本
- 筛选依据

### 4.3 丢弃非邮政数据

明确规则：

- 只有邮政系统相关内容进入 `PostalDocument`。
- 客服通用闲聊、非邮政业务、无关咨询不进入 pgvector。
- 不因为相似客服语义而保留无关数据。

### 4.4 文本切分

当前数据是对话数据，优先按对话轮次或小段对话切分，不做复杂长文档切块。

建议：

- 一个完整邮政业务问题及其上下文可以作为一个 RAG document。
- 保留必要前后轮上下文。
- 避免把多个无关问题合成一个向量。

## 5. 向量入库

### 5.1 入库命令

使用 Django management command：

```bash
python manage.py ingest_postal_rag
```

职责：

- 读取 `llm_filter`。
- 映射 CSDS 原始对话。
- 清洗文本。
- 生成 embedding。
- 写入 `PostalDocument` 和 `PostalEmbedding`。

### 5.2 幂等性

导入命令需要幂等：

- 同一个 source path + conversation id + message ids 不重复入库。
- 重复执行不会生成重复向量。
- 模型版本变化时可以重新生成 embedding。

## 6. 查询流程

用户发送消息后：

1. 保存用户消息。
2. 如果启用 RAG，使用 `qwen3-embedding:8b` 生成查询向量。
3. 在 pgvector 中做相似度搜索。
4. 取 Top K 邮政相关对话。
5. 将引用对话拼入 prompt。
6. 使用 `gpt-oss:20b` 生成回答。
7. SSE 返回引用、token、最终工单 JSON。

## 7. RAG Prompt 要求

主 prompt 需要明确：

- 你是邮政客服智能助手。
- 优先依据引用对话回答。
- 不要使用非邮政客服泛化内容。
- 不确定时说明缺少依据。
- 回答后生成工单 JSON。
- 引用内容只作为依据，不要逐字大段复述。

## 8. 引用展示

每次回答都要告诉用户引用了哪些对话。

引用信息至少包括：

- 引用编号
- 相似度分数
- 来源路径或来源 ID
- 关键片段

前端展示方式：

- AI 回答正文下方显示“引用对话”区域。
- 每条引用可折叠展开。
- 引用内容来自 `PostalDocument.content`。

## 9. SFT 模型逻辑

界面提供“监督微调模型（SFT）”勾选项。

当前状态：

- 没有可用 SFT 模型。

行为：

- 用户勾选 SFT 后，前端状态切换到 SFT 模式。
- 当前没有可用 SFT 模型，所以前端在勾选项下方显示红色提示：“当前不存在 SFT 模型”。
- 后端收到 `use_sft=true` 时必须按 SFT 模型路径处理，检查 SFT 模型是否存在。
- 如果 SFT 模型不存在，本轮请求直接返回明确错误或 SSE `error` 事件。
- 不允许静默回退到 `gpt-oss:20b`，否则用户以为正在使用 SFT，实际没有使用。
- 用户取消 SFT 勾选后，才回到普通 `gpt-oss:20b` 模式。

## 10. 会话标题生成

新会话首轮回复完成后，使用 `gpt-oss:20b` 总结对话名称。

要求：

- 标题简短。
- 中文。
- 不超过 20 个汉字。
- 不带引号。
- 不带 Markdown。

## 11. 工单 JSON 生成

工单 JSON 是关键输出。

字段建议：

```json
{
  "user_id": "",
  "timestamp": "",
  "service_type": "",
  "issue_type": "",
  "user_request": "",
  "summary": "",
  "resolution": "",
  "need_follow_up": false
}
```

### 11.1 生成策略

优先方案：

1. 使用 `gpt-oss:20b` 根据完整对话和引用依据生成严格 JSON。
2. 后端解析 JSON。
3. 使用 schema 校验字段完整性。
4. 合法则保存。
5. 不合法则触发一次修复 prompt。

备用方案：

1. 先让 `gpt-oss:20b` 生成自然语言总结。
2. 使用规则层提取字段。
3. 转换为稳定 JSON。
4. 对无法确定的字段填空字符串或 `false`。

### 11.2 校验要求

- 必须是合法 JSON。
- 不允许 Markdown code fence 包裹最终存储内容。
- 必须包含所有字段。
- `need_follow_up` 必须是 boolean。
- `timestamp` 使用 ISO 格式。

## 12. 测试重点

- `llm_filter` 到 CSDS 的映射是否正确。
- `._*.json` 是否被跳过。
- 非邮政数据是否被排除。
- embedding 查询前缀是否正确使用。
- 旧 H5 embedding 是否没有和新 embedding 混用。
- pgvector 检索是否能返回合理引用。
- SSE token 是否连续返回。
- SFT 勾选是否正确提示不可用。
- 工单 JSON 是否稳定可解析。

## 13. AI 工具包优先实现

工程实践上，先把 AI 能力做成可测试的独立工具包，全部测试通过后再接入 Django。

原因：

- 数据读取、筛选映射、embedding、检索、工单 JSON 都是核心逻辑。
- 这些逻辑不应该一开始就和 Django view、template、SSE 混在一起。
- 先做工具包可以用单元测试快速验证正确性。
- Django 只负责 Web、API、数据库事务和用户交互。

建议先实现一个可被 Django 调用的 Python 包：

```text
post_ai/
├── __init__.py
├── config.py
├── ollama_client.py
├── embeddings.py
├── source_loader.py
├── filter_mapping.py
├── retrieval.py
├── prompts.py
├── tickets.py
└── schemas.py
```

工具包职责：

- `ollama_client.py`：封装 Ollama `/api/generate`、`/api/chat`、`/api/embed`。
- `embeddings.py`：封装 `qwen3-embedding:8b`，包含 query 前缀和 document 输入规则。
- `source_loader.py`：读取 CSDS 原始数据。
- `filter_mapping.py`：读取 `llm_filter` 并映射回 CSDS。
- `retrieval.py`：提供检索输入输出结构，Django 接入时再替换为 pgvector 查询。
- `prompts.py`：集中管理 RAG prompt、标题 prompt、工单 prompt。
- `tickets.py`：生成和修复工单 JSON。
- `schemas.py`：定义 Pydantic schema，保证输出结构稳定。

工具包测试通过后，再包进 Django：

- Django `apps/llm` 调用 `post_ai.ollama_client`、`post_ai.embeddings`。
- Django `apps/rag` 调用 `post_ai.source_loader`、`post_ai.filter_mapping`。
- Django `apps/tickets` 调用 `post_ai.tickets` 和 `post_ai.schemas`。
- SSE 层只消费工具包返回的流式 token 和结构化结果。

AI 工具包测试重点：

- query embedding 输入必须等于固定前缀格式。
- document embedding 输入不能加 query instruction。
- `llm_filter` 邮政相关判断必须可测试。
- CSDS 映射失败必须返回明确错误。
- 工单 JSON schema 必须能校验合法和非法样例。
- Ollama client 可以用 mock 测试，不依赖每次真实模型运行。
