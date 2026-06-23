# 统计分析方法知识库

本目录用于系统整理 `week1/stats` 中实际使用到的统计分析与关键词提取方法。文档撰写目标并非泛泛复述教材概念，而是结合本项目的真实实现，说明各方法的基本原理、具体落地方式、适用场景与结果解释口径。

## 文档目录

- `基础统计.md`
  - 说明对话轮数、词数、token 数是怎么统计的
  - 解释为什么这里使用 `cl100k_base`，以及为什么要先去空格

- `TF-IDF.md`
  - 说明本项目如何把“单条对话”当作文档
  - 说明 `TF`、`IDF`、文档频率过滤是怎么落地实现的

- `TextRank.md`
  - 说明词共现图如何构建
  - 说明 `PageRank` 风格迭代如何得到关键词分数

- `KeyBERT.md`
  - 说明语义嵌入式关键词提取的基本思想
  - 说明本项目里如何把多条对话拼接后送入 `KeyBERT`

- `词云与可视化.md`
  - 说明普通词云、关键词词云、直方图、柱状图分别表示什么
  - 说明图是如何由 `stats/vis.py` 生成的

## 阅读说明

阅读本知识库中的文档时，建议把握以下两个前提：

1. 这些说明是围绕当前项目实现写的
2. 文中的“方法原理”只展开到足够支持项目理解和汇报的程度，不追求数学推导最完整

如需进一步追踪实现细节，可直接对照以下代码文件：

- `/Users/bizi/Desktop/邮政实习/week1/stats/basic_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/tfidf_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/textrank_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/keybert_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/vis.py`
