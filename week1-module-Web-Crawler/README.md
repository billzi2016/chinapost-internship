# 快递物流政策采集合规爬虫

本项目用于采集快递物流企业、监管机构和行业组织公开发布的政策、规则与服务条款，并在采集前执行 robots 校验、限速和来源记录。

当前阶段实现的是第一版工程骨架，重点包括：

- 配置驱动的来源管理。
- robots 校验与缓存。
- 统一请求入口与域名级限速。
- 结构化任务模型与结果导出。
- 针对保险、保价、声明价值的基础文本识别。

## 目录结构

```text
configs/
  sources.yaml
  categories.yaml
  rate_limits.yaml
crawler/
  config_loader.py
  dedupe.py
  fetcher.py
  insurance_parser.py
  models.py
  parser.py
  pdf_parser.py
  robots.py
  scheduler.py
  storage.py
main.py
tests/
```

## 设计原则

- 只抓取公开页面，不绕过限制。
- 先做合规控制，再做抓取和解析。
- 模块拆小，避免单文件和单函数过长。
- 代码和复杂逻辑使用中文注释，方便后续维护。

## 当前状态

当前版本提供：

- 来源配置加载。
- 本地任务调度入口。
- robots 规则检查。
- 限速与请求头组装。
- 原始结果持久化到 `data/` 目录。
- 保险/保价规则的关键词解析示例。

当前版本尚未提供：

- Playwright 动态渲染。
- PDF OCR。
- 大规模站点定制解析器。
- 自动增量抓取与定时任务。

## 启动方式

```bash
python3 main.py --dry-run
```

`--dry-run` 只会打印计划抓取的来源和入口链接，不会发起网络请求。
