# Week 8：综合集成、复盘与最终交付

本周目标是把前 7 周的爬虫、数据、RAG、SFT、微服务、Django Agent、报告和文档站统一收束，形成可以演示、可以复现、可以交付的完整项目。

## 主要工作

- 检查端到端链路：数据集、embedding、pgvector、FAISS、Django、FastAPI LoRA、Ollama、前端页面。
- 整理最终启动顺序和演示脚本，明确需要启动哪些服务、端口分别是什么。
- 验证四种问答组合：无 RAG 无 SFT、有 RAG 无 SFT、无 RAG 有 SFT、有 RAG 有 SFT。
- 复查 README、docs、reports 和 docs-site，确保入口清楚、命令可复制、路径不失效。
- 汇总最终结论：RAG 的作用、SFT 的作用、3B/7B 对比、当前限制和后续优化方向。
- 清理不应提交的缓存、日志、模型权重和本地 artifact。

## 最终验收清单

- PostgreSQL 和 pgvector 可用。
- Ollama embedding 模型可用。
- Django 页面可以在 `127.0.0.1:9999` 打开。
- 3B/7B LoRA FastAPI 服务至少有一个可以被 Django SFT 开关调用。
- RAG 引用能显示来源。
- 工单 JSON 可以生成、复制和下载。
- 报告 PDF 可以从 `reports/build_reports.py` 渲染。
- docs-site 可以构建，并能通过报告索引打开关键报告。

## 建议演示顺序

```bash
cd /Users/bizi/Desktop/邮政实习/week2/post-service-agent
./start_services.sh

cd /Users/bizi/Desktop/邮政实习/week3/microservice
./scripts/start_3b_lora.sh
```

然后打开：

```text
http://127.0.0.1:9999/
```

## 交付重点

Week 8 不再新增大功能，重点是稳定性、可复现性和最终叙事。任何新增内容都应优先服务于演示、复盘或交付，不再把范围继续扩大。
