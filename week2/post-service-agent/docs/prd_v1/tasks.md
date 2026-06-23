# Tasks

## 1. 项目初始化

- [x] 在 `/Users/bizi/Desktop/邮政实习/week2/post-service-agent` 创建 Django 项目。
- [x] 创建独立 AI 工具包 `post_ai`。
- [x] 配置 Django settings。
- [x] 安装并配置 django-ninja。
- [ ] 配置 PostgreSQL。
- [ ] 启用 pgvector 扩展。
- [x] 配置模型 provider。
- [x] 配置默认 chat provider 为 Ollama。
- [x] 配置默认 embedding provider 为 Ollama。
- [x] 配置 vLLM、OpenRouter、FastAPI provider 占位。
- [x] 配置 `STATIC_VERSION`。

## 2. AI 工具包

- [x] 实现 `post_ai.config`。
- [x] 定义标准 provider 接口。
- [x] 实现 provider registry。
- [x] 实现 Ollama provider。
- [x] 添加 vLLM provider 占位。
- [x] 添加 OpenRouter provider 占位。
- [x] 添加 FastAPI provider 占位。
- [x] 明确 SFT 本地权重通过独立 FastAPI 服务接入，不在 Django 内直接加载。
- [x] 实现 `qwen3-embedding:8b` query 前缀。
- [x] 实现 document embedding 无 instruction 输入。
- [x] 实现 CSDS 原始数据读取。
- [x] 实现 `llm_filter` 到 CSDS 的映射。
- [x] 实现 RAG prompt 组装。
- [x] 实现工单 JSON schema。
- [x] 实现工单 JSON 生成与修复逻辑。
- [x] 编写 AI 工具包单元测试。
- [x] AI 工具包测试全部通过后再接入 Django。

## 3. 数据核对

- [x] 检查 `/Users/bizi/Desktop/邮政实习/week2/data/CSDS` 文件结构。
- [x] 检查 `/Users/bizi/Desktop/邮政实习/week2/data/llm_filter` 文件结构。
- [x] 按 `/Users/bizi/Desktop/邮政实习/week2/prd/data_format.md` 实现数据读取。
- [x] 跳过 `CSDS/._*.json` AppleDouble 文件。
- [x] 确认 `llm_filter` 如何标识邮政相关内容。
- [x] 确认 `llm_filter` 如何映射回 CSDS 原始对话。
- [x] 校验 `index + session_id + dialogue_id` 三者一致后才允许入库。
- [ ] 明确无法映射数据的处理方式。

## 4. 数据库模型

- [ ] 按 `/Users/bizi/Desktop/邮政实习/week2/prd/database_migration.md` 设计 migration。
- [ ] 在同一个 PostgreSQL 数据库内启用 pgvector。
- [ ] 不拆业务库和向量库。
- [x] 创建 Conversation 模型。
- [x] 创建 Message 模型。
- [x] 创建 PostalDocument 模型。
- [ ] 创建 PostalEmbedding 模型。
- [x] 创建 Citation 模型。
- [x] 创建 Ticket 模型。
- [x] 创建 migrations。
- [ ] 验证 pgvector 字段可用。

## 5. RAG 入库

- [x] 实现 `llm_filter` 读取。
- [x] 实现 CSDS 原始数据映射。
- [x] 实现 `dialogue_metadata.json` 对齐校验。
- [x] 明确旧 `dialogue_embeddings.h5` 只作为参考，不和新 embedding 混用。
- [x] 实现邮政相关数据清洗。
- [x] 封装 `qwen3-embedding:8b` 调用。
- [x] 实现 embedding 前缀逻辑。
- [x] 实现 `ingest_postal_rag` management command。
- [x] 保证导入幂等。
- [x] 验证非邮政数据不会入库。

## 6. 向量检索

- [ ] 实现用户查询 embedding。
- [x] 实现 pgvector Top K 检索。
- [x] 返回引用片段、来源、相似度。
- [x] 为 RAG prompt 组装引用上下文。

## 7. LLM 服务

- [x] 封装 provider 普通生成。
- [x] 封装 provider 流式生成。
- [x] 通过默认 provider 实现 `gpt-oss:20b` 聊天回复。
- [x] 通过默认 provider 实现 `gpt-oss:20b` 会话标题总结。
- [x] 实现 SFT 模型不存在时的统一状态返回。

## 8. API 和 SSE

- [x] 创建 django-ninja API。
- [x] 实现会话列表 API。
- [x] 实现消息列表 API。
- [x] 实现发送消息接口。
- [x] 实现 SSE stream 接口。
- [x] SSE 返回 `meta`、`citation`、`delta`、`error`、`done`。
- [x] 保存用户消息和 AI 消息。
- [x] 保存引用记录。
- [x] 实现 provider health API。

## 9. Web 界面

- [x] 实现 `base.html`。
- [x] 实现聊天页面 `chat.html`。
- [x] 使用 Django templates 作为页面骨架。
- [x] 使用 Bootstrap 或少量自写 CSS 实现布局。
- [x] 固定亮色主题，不使用黑暗背景。
- [x] 不引入 React / Vue / Next.js。
- [x] 不引入独立前端构建链。
- [ ] 引入固定版本的 Markdown 渲染库。
- [ ] 引入固定版本的 Markdown sanitizer。
- [ ] 如需左侧栏拖拽宽度，使用成熟 resizable pane 小库，不手写。
- [ ] 如需代码高亮，使用成熟代码高亮库，不手写。
- [x] 左侧显示历史会话。
- [x] 左侧历史会话可点击加载。
- [x] 左侧历史会话可置顶。
- [x] 左侧历史会话可删除。
- [x] 左侧栏宽度可拖拽调整。
- [x] 右上角展示 provider health。
- [x] 左侧显示“检索增强生成（RAG）”勾选项。
- [x] 左侧显示“监督微调模型（SFT）”勾选项。
- [x] 勾选 SFT 后显示红色提示“当前不存在 SFT 模型”。
- [x] 右侧实现聊天消息区域。
- [x] 实现用户输入框和发送按钮。
- [x] 输入框支持上下拖拽调整高度。
- [x] 等待 AI 时显示三个点跳跃动画。
- [x] 展示引用对话区域。
- [ ] 前端渲染 Markdown。
- [x] CSS 和 JS 引用加版本号。

## 10. 工单 JSON

- [x] 定义工单 JSON schema。
- [x] 实现主模型直接生成 JSON。
- [x] 实现 JSON 解析和校验。
- [x] 实现失败后的修复 prompt。
- [x] 实现自然语言总结到 JSON 的备用后处理。
- [x] 前端展示工单 JSON。
- [x] 后端保存工单 JSON。
- [x] 工单按会话手动生成，不随每轮聊天自动生成。
- [x] 同一会话工单首次生成后锁定，重复点击不覆盖。
- [x] 前端支持查看已有工单。
- [x] 工单展示为左侧人类可读摘要、右侧 JSON。
- [x] 工单人类可读摘要禁止选中。
- [x] 工单 JSON 支持复制。
- [x] 前端支持下载工单 JSON。

## 11. 测试与验收

- [x] 测试 AI 工具包全部通过。
- [x] 测试数据导入不会重复。
- [x] 测试只导入邮政相关内容。
- [ ] 测试 RAG 检索能返回引用。
- [x] 测试 SSE 流式输出。
- [ ] 测试 Markdown 渲染。
- [x] 测试 SFT 不存在提示。
- [x] 测试工单 JSON 合法性。
- [ ] 进行一次完整用户对话验收。
