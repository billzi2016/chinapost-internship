# 快递物流政策采集合规爬虫

本项目用于采集快递物流企业、监管机构和行业组织公开发布的政策、规则与服务条款，并在采集过程中执行统一请求控制、限速和来源记录。

当前阶段实现的是第一版工程骨架，重点包括：

- 配置驱动的来源管理。
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
  scheduler.py
  storage.py
main.py
tests/
```

## 设计原则

- 只抓取公开页面，不绕过登录、验证码和访问控制。
- 先做合规控制，再做抓取和解析。
- 模块拆小，避免单文件和单函数过长。
- 代码和复杂逻辑使用中文注释，方便后续维护。

## 当前状态

当前版本提供：

- 来源配置加载。
- 本地任务调度入口。
- 限速与请求头组装。
- 原始结果、过滤日志和训练样本持久化到 `data/` 目录。
- 保险/保价规则的关键词解析示例。
- 训练样本质量过滤，避免把明显噪声页面混进微调数据。
- 对公开 PDF 规则文件的发现、下载和文本抽取。

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

程序运行时会输出：

- 当前阶段，例如 `dry-run`、`fetch`、`discover`。
- 当前公司和 URL。
- 已完成数量、当前队列长度。
- 基于平均耗时估算的简易 ETA。

## 一键全跑

如果你已经确认来源配置没问题，可以直接执行：

```bash
./run_full_scan.sh
```

它等价于：

```bash
python3 main.py --full-run
```

`--full-run` 会自动：

- 清空旧的 `data/` 输出目录。
- 将每个来源的页面上限提高到 `20`。
- 将候选链接发现深度提高到 `2`。
- 将终端输出同时保存到 `data/logs/full_run_YYYYMMDD_HHMMSS.log`。

最终用于微调的数据文件是：

```text
data/parsed/training_samples.jsonl
```

被过滤掉但保留审计记录的页面会写到：

```text
data/logs/filtered_pages.jsonl
```

如果来源页面里发现了公开 PDF 规则文件，程序还会额外生成：

```text
data/raw_pdfs/
data/logs/pdf_downloads.jsonl
```
