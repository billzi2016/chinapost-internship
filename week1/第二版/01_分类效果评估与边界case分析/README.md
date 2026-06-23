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

只统计 `gpt-oss:20b` 与 regex 的对比，不调用 120B：

```bash
python /Users/bizi/Desktop/邮政实习/week1/第二版/01_分类效果评估与边界case分析/run_label_comparison.py --no-ollama --limit 0
```

抽取前 50 条分歧样本，调用 `gpt-oss:120b` 复核，并显示 `tqdm` 进度条：

```bash
python /Users/bizi/Desktop/邮政实习/week1/第二版/01_分类效果评估与边界case分析/run_label_comparison.py --limit 50
```

只处理训练集，抽取前 200 条分歧样本：

```bash
python /Users/bizi/Desktop/邮政实习/week1/第二版/01_分类效果评估与边界case分析/run_label_comparison.py --split train --limit 200
```
