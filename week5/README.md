# Week 5：Django Agent 产品化与业务闭环

本周目标是把邮政客服助手从“能调用模型”推进到“能支撑业务流程”：会话、RAG、SFT、工单、前端交互和后端持久化都要形成稳定闭环。

## 主要工作

- 完善 Django + django-ninja + SSE 的聊天接口。
- 保持 RAG 和 SFT 两个开关正交：有无 RAG、有无 SFT 共四种组合都可独立验证。
- 将 SFT/LoRA 模型通过 FastAPI provider 接入，但工单生成仍由默认 `gpt-oss:20b` 链路负责。
- 完善会话历史、引用展示、重新回答、修改上一条问题、手动生成工单等交互。
- 增加时间和日期工具，供 Agent 工具调用使用。
- 为 Django 代码补充中文维护注释，降低后续继续扩展时变成单文件堆逻辑的风险。

## 当前产物

- `week2/post-service-agent/apps/api/`：API 和 SSE 编排。
- `week2/post-service-agent/apps/core/`：会话、消息、RAG 文档、引用和工单模型。
- `week2/post-service-agent/apps/web/`：Django 页面入口。
- `week2/post-service-agent/post_ai/agent_tools/`：Agent 工具目录，目前包含时间和日期工具。
- `week2/post-service-agent/tests/`：Django 和 RAG 行为测试。

## 验证方式

```bash
cd ../week2/post-service-agent
PYTHONPATH=. /opt/anaconda3/bin/python -m pytest post_ai/tests/unit -q
DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=. /opt/anaconda3/bin/python -m pytest tests/django/test_django_app.py -q
PYTHONPATH=. /opt/anaconda3/bin/python manage.py check
```

## 交付重点

- 前端页面可以清楚展示 RAG/SFT 状态。
- RAG 引用来源可回看。
- 工单 JSON 首次生成后锁定，避免后续聊天污染工单。
- Provider 抽象要继续保持，不在业务代码里写死 Ollama、FastAPI 或其他模型服务。
