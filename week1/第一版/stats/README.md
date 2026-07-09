# stats

这个目录负责 `CSDS` 的基础统计、三种关键词分析和可视化。

## 文件说明

- `dataloader.py`：读取 `train.json`、`val.json`、`test.json`
- `basic_analysis.py`：统计对话轮数、token 数、词数，并保存 `summary.json`
- `tfidf_analysis.py`：按“单条完整对话 = 一个 document”计算对话级 `TF-IDF`
- `textrank_analysis.py`：用 TextRank 提取关键词
- `keybert_analysis.py`：用 KeyBERT 提取关键词
- `keyword_utils.py`：多种关键词方法共享的清洗与路径工具
- `vis.py`：生成直方图、词频图、普通词云，以及 `TF-IDF / TextRank / KeyBERT` 的 Top20 图与词云
- `main.py`：统一入口

## 输出目录

- `outputs/basic_analysis/summary.json`
- `outputs/tfidf/tfidf_keywords.json`
- `outputs/tfidf/tfidf_keywords.txt`
- `outputs/textrank/textrank_keywords.json`
- `outputs/textrank/textrank_keywords.txt`
- `outputs/keybert/keybert_keywords.json`
- `outputs/keybert/keybert_keywords.txt`
- `outputs/vis/*.png`

## 统计口径

- token 数：先去掉空格，再用 `cl100k_base` 编码统计
- 词数：直接基于原始已分词文本，用空格切分统计
- `TF-IDF / TextRank / KeyBERT`：统一以“单条完整对话”为一个 document，而不是单轮 utterance

## 关键词方案

- `TF-IDF`：保留可控、可解释的统计基线
- `TextRank`：基于共现图和 PageRank 的传统改良方案
- `KeyBERT`：基于语义嵌入的关键词方案，通常比单纯词频更抗停用词噪声

## 依赖说明

- `KeyBERT` 需要本地安装 `keybert` 及其依赖
- 如果未安装，`main.py` 仍可运行，但会跳过 KeyBERT 结果

## 关于 KeyBERT 的实现取舍

- 当前 `KeyBERT` 采用的是官方推荐的简洁调用方式
- 没有强行在这一层额外塞 `CPU // 2`、进度条或 batch 控制
- 原因是这些能力不是 `KeyBERT.extract_keywords(...)` 这一层原生直接提供的干净参数
- 如果后续真的要精细控制设备、batch 或更细粒度进度，应该改为显式构造底层 `SentenceTransformer` 模型，再传给 `KeyBERT`
- 当前版本优先保持代码可读性和职责清晰，不为了强行加控制项把实现写得过重

## 安装方式

```bash
cd .
pip install -r requirements.txt
```

## 运行方式

```bash
python main.py
```
