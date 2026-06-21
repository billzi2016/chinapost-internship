# 知识库

本目录用于整理 `week1/stats` 中实际使用到的方法说明，目标不是写成泛泛的教材，而是把**本项目代码里到底怎么做的**、**背后的基本原理是什么**、**为什么这样用**说明清楚。

## 文档列表

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

## 使用原则

阅读这些文档时，需要记住两个前提：

1. 这些说明是围绕当前项目实现写的
2. 文中的“方法原理”只展开到足够支持项目理解和汇报的程度，不追求数学推导最完整

如果需要追踪到具体代码，可以直接对应查看：

- `/Users/bizi/Desktop/邮政实习/week1/stats/basic_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/tfidf_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/textrank_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/keybert_analysis.py`
- `/Users/bizi/Desktop/邮政实习/week1/stats/vis.py`
