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
