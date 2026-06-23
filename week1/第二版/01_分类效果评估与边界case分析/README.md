# 01 分类效果评估与边界 case 分析

## 对应反馈

`gpt-oss:20b` 的模型做二分类任务，对于分好的结果是否做过探查；整体情况如何；是否存在边界 case；有没有量化指标评估分类效果；可以用正则分析数据中总结部分的关键词来给数据打标签。

## 计划解决内容

- 汇总 `week2/data/llm_filter/postal_filter_results.json` 中的二分类结果。
- 统计各 split 中邮政相关与非邮政相关样本数量、比例。
- 从 CSDS 原始数据中提取对话文本和总结字段，基于关键词正则构造弱标签。
- 将 LLM 标签与正则弱标签进行对比，给出一致率、疑似误判样本和边界 case。
- 输出可写入报告的分类效果评估结论。

## 输入数据

- `week2/data/llm_filter/postal_filter_results.json`
- `week2/data/CSDS/train.json`
- `week2/data/CSDS/val.json`
- `week2/data/CSDS/test.json`

## 预期输出

- 二分类整体统计表
- 正则弱标签规则说明
- LLM 标签与正则弱标签对比结果
- 边界 case 样本列表
- 报告补充段落

## 当前产出

- `01_04_合并分析方案.md`
- `run_label_comparison.py`

当前判断：01 和 04 应合并为“标签质量评估 + 业务主题细分”流程。  
其中 01 侧重点是 regex 弱标签和二分类效果评估，04 侧重点是 `gpt-oss:120b` 细分业务类，并将分类结果用于可视化标签。

## 运行方式

脚本会根据自身位置自动向上查找同时包含 `week1` 和 `week2` 的项目根目录，因此不依赖当前终端所在目录。

建议先进入本目录：

```bash
cd week1/第二版/01_分类效果评估与边界case分析
```

只统计 `gpt-oss:20b` 与 regex 的对比，不调用 120B：

```bash
python run_label_comparison.py --no-ollama --limit 0
```

抽取前 50 条分歧样本，调用 `gpt-oss:120b` 复核，并显示 `tqdm` 进度条：

```bash
python run_label_comparison.py --limit 50
```

只处理训练集，抽取前 200 条分歧样本：

```bash
python run_label_comparison.py --split train --limit 200
```

运行全部分歧样本，让 `gpt-oss:120b` 复核所有 `gpt-oss:20b` 与 regex 不一致的样本：

```bash
python run_label_comparison.py --limit 0
```

运行全部样本，不只复核分歧样本：

```bash
python run_label_comparison.py --review-policy all --limit 0
```

最全运行方式：全部样本都交给 `gpt-oss:120b` 复核，并显式使用 `think=low`：

```bash
python run_label_comparison.py --review-policy all --limit 0 --think low
```

## 保存与断点续跑

默认保存策略：

- `gpt-oss:120b` 复核结果写入 `outputs/120b_review_results.jsonl`
- 默认每 `100` 条批量保存一次，减少频繁写 SSD
- 每条结果以 `split:index` 作为唯一键
- 脚本重新运行时会读取已有 `outputs/120b_review_results.jsonl`
- 已经完成的样本会自动跳过，继续跑剩余样本

也就是说，如果中途断了，直接重新运行同一条命令即可续跑。

调整保存频率：

```bash
python run_label_comparison.py --limit 0 --save-every 200
```

如果希望更保守，减少断点损失，可以改小：

```bash
python run_label_comparison.py --limit 0 --save-every 50
```

## 120B thinking 设置

脚本默认调用 `gpt-oss:120b` 时会传入：

```bash
--think low
```

这样可以减少长 reasoning 带来的耗时。

默认已经是 `low`，正常运行不需要额外指定：

```bash
python run_label_comparison.py --limit 0
```

可选值只有 `low`、`medium`、`high`。如果需要更充分的推理，可以手动覆盖：

```bash
python run_label_comparison.py --limit 0 --think medium
python run_label_comparison.py --limit 0 --think high
```
