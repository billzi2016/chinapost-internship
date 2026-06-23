# Django Plan

## 1. 项目目标

在 `/Users/bizi/Desktop/邮政实习/week2/post-service-agent` 下建设一个正式的邮政客服智能助手系统。

系统核心能力：

- 使用 Django 提供 Web 应用基础。
- 使用 django-ninja 提供结构化 API。
- 使用 SSE 实现 AI 回复流式输出。
- 使用 PostgreSQL 存储业务数据。
- 使用 pgvector 存储和检索邮政相关对话向量。
- 使用 Django templates、HTML、CSS、JavaScript 实现正式 Web 界面。
- 模型调用通过标准 provider 接口，当前默认使用 Ollama 本地模型：
  - 主模型：`gpt-oss:20b`
  - 向量模型：`qwen3-embedding:8b`
- vLLM、OpenRouter、自建 FastAPI 模型服务作为 provider 占位。
- SFT 不在 Django 进程内直接加载 Transformers 权重；如需本地 SFT，由用户单独启动 FastAPI 模型服务。
- 根据 RAG 引用结果生成回答，并展示引用了哪些原始对话。
- 最终生成稳定合法的工单 JSON。

本项目不引入当前没有必要的复杂组件，例如 GraphQL、WebSocket、Celery、RabbitMQ、分库分表、sharding 等。

## 2. 技术边界

### 2.1 必选技术

- Python
- Django
- django-ninja
- PostgreSQL
- pgvector
- Server-Sent Events
- Django templates
- HTML
- CSS
- JavaScript
- Ollama provider
- vLLM provider 占位
- OpenRouter provider 占位
- FastAPI provider 占位

### 2.2 明确不做

- 不做 GraphQL。
- 不做 WebSocket。
- 不做 Celery / RabbitMQ。
- 不做分布式队列。
- 不做 sharding。
- 不做微服务拆分。
- 不做前后端完全分离 SPA。
- 不引入 React / Vue / Next.js 等前端架构。
- 不引入独立前端构建链。

## 3. Django 项目原则

项目按正式工程组织，但保持当前规模下的 KISS：

- AI 核心能力先做成独立 `post_ai` 工具包，测试通过后再接入 Django。
- templates 相关页面单独放在 `apps/web`，不塞进 RAG 或聊天业务 app。
- 前端页面使用 Django templates 做骨架。
- 页面布局可以参考 Chatbot UI / Open WebUI 的信息架构，但不能直接引入完整前端项目。
- UI 实现使用 Bootstrap 或少量自写 CSS。
- UI 固定使用亮色主题，不做黑暗背景。
- 交互使用原生 JavaScript。
- Markdown 渲染使用成熟 JS 库。
- SSE 只写必要连接和事件处理逻辑，不造前端框架。
- 左侧栏拖拽宽度、Markdown 清洗、代码高亮等基础能力使用成熟小库或 Bootstrap 现成组件，不手写脆弱实现。
- 如果某个交互没有合适轻量依赖，优先降级为简单稳定方案。
- API 层放在 `apps/api`，统一挂载 django-ninja router。
- 当前规模下不拆 `conversations/rag/llm/tickets` 多个 app，避免为了分层而分层。
- Django 只保留 `apps/core`、`apps/api`、`apps/web` 三个 app。
- `apps/core` 放 ORM 数据模型：会话、消息、邮政文档、引用、工单。
- `apps/api` 放 django-ninja API 和 SSE 编排。
- `apps/web` 放 templates 页面和静态资源入口。
- 模型 provider、embedding 前缀、数据映射、prompt、工单 JSON 生成优先放在 `post_ai`，Django service 层只做业务编排。
- 数据导入使用 Django management command。
- 配置使用 `.env`，不要把模型名、数据库连接写死在业务代码里。
- 遵循 DRY、KISS、SOLID，但不为了模式而抽象。

## 4. 应用划分

### 4.1 `config`

Django 项目配置目录。

职责：

- `settings.py`
- `urls.py`
- `asgi.py`
- `wsgi.py`

### 4.2 `apps/web`

Web 页面入口。

职责：

- 渲染聊天主界面。
- 管理 templates。
- 组织静态资源入口。
- 提供页面级 view。

### 4.3 `apps/api`

django-ninja API 入口。

职责：

- 统一创建 `NinjaAPI`。
- 挂载 chat、conversation、ticket 等 router。
- 统一 API 错误格式。

### 4.4 `apps/core`

Django ORM 核心数据层。

职责：

- 存储聊天会话。
- 存储用户消息、AI 消息。
- 存储邮政相关原始对话片段。
- 存储引用记录。
- 存储工单 JSON。
- 后续接 PostgreSQL + pgvector 时，存储 `PostalEmbedding`。

不做的事：

- 不在 `apps/core` 里写模型 provider。
- 不在 `apps/core` 里写 prompt。
- 不在 `apps/core` 里写 CSDS/llm_filter 映射。
- 这些 AI 能力继续由完整的 `post_ai` 包负责。

## 5. 数据来源

数据目录：

- 原始数据：`/Users/bizi/Desktop/邮政实习/week2/data/CSDS`
- 已筛选信息：`/Users/bizi/Desktop/邮政实习/week2/data/llm_filter`
- 已移动 embedding 输出：`/Users/bizi/Desktop/邮政实习/week2/data/embeddings`

处理规则：

- `llm_filter` 已判断哪些内容与邮政系统相关。
- 只保留邮政相关数据。
- 其他客服泛化内容一律不进入 pgvector。
- 导入时需要能从筛选结果映射回原始 CSDS 对话。

## 6. 数据库设计

### 6.1 Conversation

字段建议：

- `id`
- `title`
- `created_at`
- `updated_at`

### 6.2 Message

字段建议：

- `id`
- `conversation_id`
- `role`
- `content`
- `created_at`

`role` 取值：

- `user`
- `assistant`
- `system`

### 6.3 PostalDocument

存储进入 RAG 的邮政相关原始对话片段。

字段建议：

- `id`
- `source_dataset`
- `source_path`
- `source_conversation_id`
- `source_message_ids`
- `content`
- `metadata`
- `created_at`

### 6.4 PostalEmbedding

存储 pgvector 向量。

字段建议：

- `id`
- `document_id`
- `embedding`
- `embedding_model`
- `created_at`

`embedding` 使用 pgvector 类型。

### 6.5 Citation

存储一次回答引用了哪些对话。

字段建议：

- `id`
- `message_id`
- `document_id`
- `score`
- `quoted_text`
- `created_at`

### 6.6 Ticket

存储最终工单 JSON。

字段建议：

- `id`
- `conversation_id`
- `message_id`
- `payload`
- `is_valid`
- `validation_error`
- `created_at`

## 7. API 设计

### 7.1 会话 API

- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `PATCH /api/conversations/{conversation_id}`

### 7.2 消息 API

- `GET /api/conversations/{conversation_id}/messages`
- `POST /api/conversations/{conversation_id}/messages`

### 7.3 SSE 聊天接口

- `GET /api/chat/stream`

参数：

- `conversation_id`
- `message`
- `use_rag`
- `use_sft`

行为：

- 写入用户消息。
- 如果 `use_rag=true`，执行配置的 vector provider 检索。
- 当前阶段 vector provider 为 FAISS。
- pgvector provider 作为后续 PostgreSQL 阶段实现，不把占位当完成。
- 如果 `use_sft=true`，检查 SFT provider 和模型配置。
- 当前没有 SFT 模型时返回前端可展示错误状态，并停止本轮生成。
- `use_sft=true` 时不允许静默回退到 `gpt-oss:20b`。
- 只有 `use_sft=false` 时，才通过默认 chat provider 使用 `gpt-oss:20b` 流式生成回答。
- SSE 事件中逐步返回 token、引用和结束状态。
- 工单 JSON 不随每轮聊天自动生成，改由用户在会话级别手动生成。

### 7.4 工单 API

- `GET /api/conversations/{conversation_id}/ticket`
- `POST /api/conversations/{conversation_id}/ticket/generate`
- 同一会话工单首次生成后锁定，后续重复请求返回已有工单，不覆盖、不新增。
- `GET /api/provider/health`

## 8. SSE 事件格式

建议事件：

- `meta`
- `citation`
- `delta`
- `error`
- `done`

示例：

```text
event: delta
data: {"content": "您好，"}
```

```text
event: citation
data: {"document_id": 12, "score": 0.82, "quoted_text": "..."}
```

## 9. 静态资源版本策略

CSS 和 JS 必须带版本，避免浏览器缓存导致改动不生效。

建议方式：

- settings 中定义 `STATIC_VERSION`。
- 模板引用：

```django
<link rel="stylesheet" href="{% static 'web/css/chat.css' %}?v={{ static_version }}">
<script src="{% static 'web/js/chat.js' %}?v={{ static_version }}" defer></script>
```

## 10. Markdown 渲染

AI 回复需要支持 Markdown：

- 段落
- 列表
- 表格
- 代码块
- 引用
- 加粗
- 标题

实现方式：

- 后端保存原始 Markdown。
- 前端使用成熟 Markdown 渲染库。
- 前端必须做 XSS 防护，使用成熟 sanitizer。

## 11. 工单 JSON

工单 JSON 是核心功能，不是附属功能。

目标字段：

- `user_id`
- `timestamp`
- `service_type`
- `issue_type`
- `user_request`
- `summary`
- `resolution`
- `need_follow_up`

要求：

- 字段完整。
- 输出合法 JSON。
- 字段名稳定。
- 类型稳定。
- 前端可以直接解析并展示。

如果主模型 JSON 输出不稳定：

- 第一步让主模型生成自然语言总结。
- 第二步使用规则层或小模型把总结转换为 JSON。
- 第三步后端使用 schema 校验，不合法则重试或返回错误。

## 12. 验收标准

- 启动 Django 后可以进入聊天页面。
- 左侧能看到历史会话。
- 右侧能发送消息并通过 SSE 看到流式回复。
- 等待 AI 时有三点跳跃动画。
- 勾选 RAG 后会使用当前配置的 vector provider；当前为 FAISS，后续切 pgvector。
- 勾选 SFT 后提示当前不存在 SFT 模型。
- 每次回答能展示引用了哪些原始对话。
- AI 回复能渲染 Markdown。
- 会话标题由 `gpt-oss:20b` 总结生成。
- 最终能生成合法工单 JSON。
