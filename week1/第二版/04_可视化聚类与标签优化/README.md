# 04 可视化聚类与标签优化

## 对应反馈

可视化时需要更明显看出不同簇，可以尝试每个点带标签，或者用聚类方法，观察大概分为几类，例如费率价格类、时限时效类、流程规则类、禁限寄类、国际业务类等。

## 计划解决内容

- 基于 `week2/data/embeddings/dialogue_embeddings.h5` 和 `dialogue_metadata.json` 读取 embedding 与元数据。
- 对 LLM 判为邮政相关的样本进行聚类分析。
- 用关键词规则或聚类中心样本解释簇含义。
- 生成带业务标签的可视化图，补充原有 PCA、t-SNE、UMAP 结果。
- 对聚类结果总结为若干业务类型。

## 输入数据

- `week2/data/embeddings/dialogue_embeddings.h5`
- `week2/data/embeddings/dialogue_metadata.json`
- `week2/data/llm_filter/postal_filter_results.json`
- `week2/data/CSDS/train.json`
- `week2/data/CSDS/val.json`
- `week2/data/CSDS/test.json`

## 预期输出

- 聚类类别统计
- 聚类可视化图片
- 每类代表关键词或代表样本
- 报告补充段落

## 当前产出

- `../01_分类效果评估与边界case分析/01_04_合并分析方案.md`

当前判断：04 不应单独只做聚类图，而应接入 01 的标签质量评估结果。  
推荐做法是：先用 regex 收紧严格邮政 / EMS 标签，再用 `gpt-oss:120b` 对边界样本和代表样本细分业务类，最后把业务类作为可视化标签。
