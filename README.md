# 邮政实习项目

本仓库按周整理邮政客服数据分析、RAG 智能客服和语音转写相关实验代码。当前主要包含 `week1`、`week2` 和 `Whisper-main` 三部分。

## Week 1

`week1` 主要是邮政客服数据的前期筛选、统计分析和可视化验证。

- `week1/第一版`：包含早期的数据筛选、关键词统计、词云、聚类可视化、模型选型和风险控制说明。
- `week1/第二版`：补充分类效果评估、边界 case 分析、模型选型说明、代码仓库管理说明，以及可视化聚类和标签优化记录。
- 核心目标是把邮政相关对话从客服泛化数据中筛出来，为第二周 RAG 系统准备干净数据。

## Week 2

`week2` 主要是邮政智能客服 RAG 系统。

- `week2/data`：存放原始数据、筛选后的邮政相关数据、embedding 数据和 SFT 训练数据占位。
- `week2/post-service-agent`：正式 Django 项目，集成 Django、Django Ninja、SSE、PostgreSQL、pgvector、Ollama 和独立 `post_ai` 工具包。
- 当前系统支持左侧会话历史、右侧聊天窗口、RAG 引用展示、工单 JSON 生成、Markdown 渲染、Provider 健康提示，以及 PostgreSQL + pgvector 向量检索。
- 设计上保留 FAISS/local 和 PostgreSQL-pgvector/microservice 两种模式，便于本地调试和正式服务切换。

配套工具：

- Postman：用于接口请求调试和 API 验证。
- DBeaver：用于连接 PostgreSQL，查看会话、消息、工单和向量数据表。

## Week 2 界面截图

![Django Week 2 界面](django_week2.png)

## Whisper-main

`Whisper-main` 是用于对公开会议和课程内容进行批量自动化精确转录的工具，支持音视频输入、字幕生成和转写结果整理。代码可以纳入版本控制，但运行时产生的大文件不进入 git：

- `Whisper-main/media/`：音视频输入文件，已忽略。
- `Whisper-main/subtitles/`：字幕输出文件，已忽略。

## 运行入口

邮政智能客服项目的启动、数据库迁移、PostgreSQL、Ollama 和 Django 服务说明在：

- `week2/post-service-agent/README.md`
- `week2/post-service-agent/QUICKSTART.md`
- `week2/post-service-agent/docs/`

Swagger / API 文档入口在 Django 服务启动后的：

- `http://127.0.0.1:9999/api/docs`

## Swagger 截图

![Week 2 Swagger API 文档](127.0.0.1_9999_api_docs_week2.png)
