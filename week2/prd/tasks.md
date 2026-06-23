# Tasks

## 1. 项目初始化

- [ ] 在 `/Users/bizi/Desktop/邮政实习/week2/post-service-agent` 创建 Django 项目。
- [ ] 创建独立 AI 工具包 `post_ai`。
- [ ] 配置 Django settings。
- [ ] 安装并配置 django-ninja。
- [ ] 配置 PostgreSQL。
- [ ] 启用 pgvector 扩展。
- [ ] 配置模型 provider。
- [ ] 配置默认 chat provider 为 Ollama。
- [ ] 配置默认 embedding provider 为 Ollama。
- [ ] 配置 vLLM、OpenRouter、FastAPI provider 占位。
- [ ] 配置 `STATIC_VERSION`。

## 2. AI 工具包

- [ ] 实现 `post_ai.config`。
- [ ] 定义标准 provider 接口。
- [ ] 实现 provider registry。
- [ ] 实现 Ollama provider。
- [ ] 添加 vLLM provider 占位。
- [ ] 添加 OpenRouter provider 占位。
- [ ] 添加 FastAPI provider 占位。
- [ ] 明确 SFT 本地权重通过独立 FastAPI 服务接入，不在 Django 内直接加载。
- [ ] 实现 `qwen3-embedding:8b` query 前缀。
- [ ] 实现 document embedding 无 instruction 输入。
- [ ] 实现 CSDS 原始数据读取。
- [ ] 实现 `llm_filter` 到 CSDS 的映射。
- [ ] 实现 RAG prompt 组装。
- [ ] 实现工单 JSON schema。
- [ ] 实现工单 JSON 生成与修复逻辑。
- [ ] 编写 AI 工具包单元测试。
- [ ] AI 工具包测试全部通过后再接入 Django。

## 3. 数据核对

- [ ] 检查 `/Users/bizi/Desktop/邮政实习/week2/data/CSDS` 文件结构。
- [ ] 检查 `/Users/bizi/Desktop/邮政实习/week2/data/llm_filter` 文件结构。
- [ ] 按 `/Users/bizi/Desktop/邮政实习/week2/prd/data_format.md` 实现数据读取。
- [ ] 跳过 `CSDS/._*.json` AppleDouble 文件。
- [ ] 确认 `llm_filter` 如何标识邮政相关内容。
- [ ] 确认 `llm_filter` 如何映射回 CSDS 原始对话。
- [ ] 校验 `index + session_id + dialogue_id` 三者一致后才允许入库。
- [ ] 明确无法映射数据的处理方式。

## 4. 数据库模型

- [ ] 按 `/Users/bizi/Desktop/邮政实习/week2/prd/database_migration.md` 设计 migration。
- [ ] 在同一个 PostgreSQL 数据库内启用 pgvector。
- [ ] 不拆业务库和向量库。
- [ ] 创建 Conversation 模型。
- [ ] 创建 Message 模型。
- [ ] 创建 PostalDocument 模型。
- [ ] 创建 PostalEmbedding 模型。
- [ ] 创建 Citation 模型。
- [ ] 创建 Ticket 模型。
- [ ] 创建 migrations。
- [ ] 验证 pgvector 字段可用。

## 5. RAG 入库

- [ ] 实现 `llm_filter` 读取。
- [ ] 实现 CSDS 原始数据映射。
- [ ] 实现 `dialogue_metadata.json` 对齐校验。
- [ ] 明确旧 `dialogue_embeddings.h5` 只作为参考，不和新 embedding 混用。
- [ ] 实现邮政相关数据清洗。
- [ ] 封装 `qwen3-embedding:8b` 调用。
- [ ] 实现 embedding 前缀逻辑。
- [ ] 实现 `ingest_postal_rag` management command。
- [ ] 保证导入幂等。
- [ ] 验证非邮政数据不会入库。

## 6. 向量检索

- [ ] 实现用户查询 embedding。
- [ ] 实现 pgvector Top K 检索。
- [ ] 返回引用片段、来源、相似度。
- [ ] 为 RAG prompt 组装引用上下文。

## 7. LLM 服务

- [ ] 封装 provider 普通生成。
- [ ] 封装 provider 流式生成。
- [ ] 通过默认 provider 实现 `gpt-oss:20b` 聊天回复。
- [ ] 通过默认 provider 实现 `gpt-oss:20b` 会话标题总结。
- [ ] 实现 SFT 模型不存在时的统一状态返回。

## 8. API 和 SSE

- [ ] 创建 django-ninja API。
- [ ] 实现会话列表 API。
- [ ] 实现消息列表 API。
- [ ] 实现发送消息接口。
- [ ] 实现 SSE stream 接口。
- [ ] SSE 返回 `meta`、`citation`、`delta`、`ticket`、`error`、`done`。
- [ ] 保存用户消息和 AI 消息。
- [ ] 保存引用记录。

## 9. Web 界面

- [ ] 实现 `base.html`。
- [ ] 实现聊天页面 `chat.html`。
- [ ] 使用 Django templates 作为页面骨架。
- [ ] 使用 Bootstrap 或少量自写 CSS 实现布局。
- [ ] 固定亮色主题，不使用黑暗背景。
- [ ] 不引入 React / Vue / Next.js。
- [ ] 不引入独立前端构建链。
- [ ] 引入固定版本的 Markdown 渲染库。
- [ ] 引入固定版本的 Markdown sanitizer。
- [ ] 如需左侧栏拖拽宽度，使用成熟 resizable pane 小库，不手写。
- [ ] 如需代码高亮，使用成熟代码高亮库，不手写。
- [ ] 左侧显示历史会话。
- [ ] 左侧显示“检索增强生成（RAG）”勾选项。
- [ ] 左侧显示“监督微调模型（SFT）”勾选项。
- [ ] 勾选 SFT 后显示红色提示“当前不存在 SFT 模型”。
- [ ] 右侧实现聊天消息区域。
- [ ] 实现用户输入框和发送按钮。
- [ ] 等待 AI 时显示三个点跳跃动画。
- [ ] 展示引用对话区域。
- [ ] 前端渲染 Markdown。
- [ ] CSS 和 JS 引用加版本号。

## 10. 工单 JSON

- [ ] 定义工单 JSON schema。
- [ ] 实现主模型直接生成 JSON。
- [ ] 实现 JSON 解析和校验。
- [ ] 实现失败后的修复 prompt。
- [ ] 实现自然语言总结到 JSON 的备用后处理。
- [ ] 前端展示工单 JSON。
- [ ] 后端保存工单 JSON。

## 11. 测试与验收

- [ ] 测试 AI 工具包全部通过。
- [ ] 测试数据导入不会重复。
- [ ] 测试只导入邮政相关内容。
- [ ] 测试 RAG 检索能返回引用。
- [ ] 测试 SSE 流式输出。
- [ ] 测试 Markdown 渲染。
- [ ] 测试 SFT 不存在提示。
- [ ] 测试工单 JSON 合法性。
- [ ] 进行一次完整用户对话验收。
