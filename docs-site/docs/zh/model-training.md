# 模型微调结论

当前文档站点对 LoRA 微调部分保留的是一版整理后的统一口径，不再把所有实验波动逐条展开。这部分和 RAG 一起构成了项目最核心的两条主线之一。

## 3B 模型

当前保留的结论是：

```text
Qwen2.5-3B -> rank 2
```

这个结论对应的是当前整理版文档中更适合持续引用的一版结果。

![Qwen2.5 3B LoRA 微调](https://raw.githubusercontent.com/billzi2016/chinapost-internship/main/images/3b-lora.png)

![Qwen2.5 3B FastAPI 推理服务](https://raw.githubusercontent.com/billzi2016/chinapost-internship/main/images/3b-fastapi.png)

## 7B 模型

当前保留的结论是：

```text
Qwen2.5-7B -> rank 4
```

## 说明

这类 LoRA rank 结果本身带有一定随机性，因此当前文档站点保留的是一版统一结论，用来服务说明、整理和后续复现口径，而不是把每轮实验波动都放到站点首页层面。

如果继续往下补完整实验细节，应以 `week3/reports/` 和 `reports/step3_lora微调/` 中的整理材料为准。
