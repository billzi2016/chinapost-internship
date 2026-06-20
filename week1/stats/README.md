# stats

这个目录负责 `CSDS` 的基础统计、关键词分析和可视化。

## 文件说明

- `dataloader.py`：读取 `train.json`、`val.json`、`test.json`
- `basic_analysis.py`：统计对话轮数、token 数、词数，并保存 `summary.json`
- `advanced_analysis.py`：按“单条完整对话 = 一个 document”计算对话级 `TF-IDF`
- `vis.py`：生成直方图、词频图、普通词云、`TF-IDF` 词云
- `main.py`：统一入口

## 输出目录

- `outputs/basic_analysis/summary.json`
- `outputs/advanced_analysis/tfidf_keywords.json`
- `outputs/advanced_analysis/tfidf_keywords.txt`
- `outputs/vis/*.png`

## 统计口径

- token 数：先去掉空格，再用 `cl100k_base` 编码统计
- 词数：直接基于原始已分词文本，用空格切分统计
- `TF-IDF`：以“单条完整对话”为一个文档，而不是单轮 utterance

## 运行方式

```bash
python /Users/bizi/Desktop/邮政实习/week1/stats/main.py
```
