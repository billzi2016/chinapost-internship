# QUICKSTART

本文档用于说明如何在本地运行完整程序，以及如何先做低风险验证。

如果你只想直接全跑，不想自己拼参数，直接执行：

```bash
./run_full_scan.sh
```

或者：

```bash
python3 main.py --full-run
```

## 1. 环境准备

- Python 3.11 及以上。
- 建议先安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

如果暂时没有安装 `httpx`，程序会自动回退到 Python 标准库请求方式，但完整体验仍建议安装依赖。

## 2. 先做 dry-run

先验证配置、入口脚本和任务调度，不访问目标站点：

```bash
python3 main.py --dry-run --max-pages-per-source 3
```

你会看到类似输出：

```text
[DRY-RUN][depth=0] 中国邮政 EMS: https://www.ems.com.cn/
[PROGRESS] stage=dry-run company=中国邮政 EMS completed=1 queued=2 eta≈0s url=https://www.ems.com.cn/
```

## 3. 小批量真实抓取

每个来源先抓少量页面，验证 robots、请求器、落盘和解析：

```bash
python3 main.py --max-pages-per-source 2
```

建议先从 `2` 或 `3` 开始，不要一开始就跑太大。

## 3.1 一键完整抓取

当你确认当前 `configs/sources.yaml` 已经补全到你要的来源后，可以直接执行：

```bash
./run_full_scan.sh
```

这条命令会自动：

- 清空旧的 `data/` 目录。
- 对当前配置里的所有来源启动抓取。
- 将每个来源页面上限设为 `20`。
- 将候选链接发现深度设为 `2`。
- 保留 robots 校验、进度提示和结果落盘。
- 将终端输出同时保存到 `data/logs/full_run_YYYYMMDD_HHMMSS.log`。

## 4. 输出目录

运行后会生成：

- `data/logs/robots_report.jsonl`：robots 校验结果。
- `data/logs/fetch_results.jsonl`：抓取结果和失败原因。
- `data/logs/filtered_pages.jsonl`：被过滤掉的低质量页面，只用于审计，不进入训练样本。
- `data/logs/full_run_YYYYMMDD_HHMMSS.log`：完整运行日志，同时也会在屏幕显示。
- `data/logs/pdf_downloads.jsonl`：公开 PDF 文件的下载记录。
- `data/parsed/policies.jsonl`：结构化政策记录。
- `data/parsed/training_samples.jsonl`：最终保留下来的微调样本文件。
- `data/logs/crawl_report.md`：抓取汇总报告。
- `data/raw_pdfs/`：保存下来的原始 PDF 文件。

## 5. 运行过程中的进度提示

程序默认会输出文本进度，不依赖 `tqdm`：

- `stage`：当前阶段，例如 `fetch`。
- `company`：当前来源。
- `completed`：已完成任务数。
- `queued`：当前等待队列长度。
- `eta`：基于平均耗时估算的剩余时间。

另外还会输出：

- `[FETCH]`：当前页面抓取结果。
- `[DISCOVER]`：当前页面发现了多少个候选 policy 链接。

## 6. 跑完整程序前建议

- 先检查 `configs/sources.yaml`，按你的目标公司继续补来源。
- 先用小值验证 `--max-pages-per-source`，确认过滤没有误抓静态资源。
- 先观察 `robots_report.jsonl` 和 `fetch_results.jsonl`，确认站点允许且返回的是公开页面。
- 真正用于后续微调的数据应以 `data/parsed/training_samples.jsonl` 为准，不要直接把全部抓取日志送去训练。
- 对动态站点、首页跳转站点和 PDF 站点，后续再补专门解析器。
- 对扫描版图片 PDF，当前仍不做 OCR。

## 7. 当前已知限制

- 目前主要支持首页和首页发现的第一层政策链接。
- 还没有做 Playwright 动态渲染。
- 已支持公开 PDF 的下载和文本抽取，但扫描版图片 PDF 仍不支持 OCR。
- 还没有做更细的站点级规则模板。
