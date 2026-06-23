# PRD：基于 Apple MLX 微调 Qwen2.5 3B / 7B 邮政客服模型

## 1. 项目背景

本项目第三周目标是在本地 Apple Silicon 设备上，基于已有邮政客服数据，对 Qwen2.5 系列模型进行监督微调，使模型更适合邮政、EMS、快递咨询、业务规则解释、用户问题归纳与客服回复生成等垂直场景。

本阶段不采用复杂的第三方训练脚手架，优先使用 Apple 官方维护的 `mlx-lm` 作为主训练工具。`mlx-lm` 对 Apple Silicon 的统一内存和 Metal 后端支持更稳定，适合在 Mac 本地完成 LoRA 微调、推理验证和权重融合。

## 2. 项目目标

### 2.1 核心目标

使用 `mlx-lm` 在 Apple MLX 环境下分别微调：

- `Qwen/Qwen2.5-3B-Instruct`
- `Qwen/Qwen2.5-7B-Instruct`

训练方式以 LoRA 为主，必要时评估 QLoRA 或量化加载方案，最终产出可复现实验配置、训练日志、LoRA Adapter 权重和推理测试结果。

### 2.2 非目标

本阶段不做以下事项：

- 不训练 14B、32B 或更大模型。
- 不从零预训练模型。
- 不引入复杂分布式训练框架。
- 不把 `gpt-oss` 作为被微调模型。
- 不在 PRD 阶段直接运行训练命令。

## 3. 数据来源

当前数据目录如下，所有脚本和配置应使用相对路径引用：

```text
../week2/data/
../week2/data/sft_training/
```

推荐优先使用 `sft_training` 中已经整理好的监督微调数据。如果后续发现格式不完全符合 `mlx-lm` 要求，再增加一个轻量转换脚本，将现有数据转换为 JSONL 格式。

## 4. 数据格式要求

`mlx-lm` 推荐使用 OpenAI Chat 风格 JSONL。每一行是一个完整 JSON 对象，不能跨行。

标准样例如下：

```json
{"messages":[{"role":"system","content":"你是一个专业、准确、克制的邮政客服助手。"},{"role":"user","content":"EMS 快递一直没有更新物流怎么办？"},{"role":"assistant","content":"建议先通过 EMS 官方渠道使用运单号查询最新状态。如果物流长时间未更新，可以联系寄件网点或 EMS 客服核实是否存在揽收、运输、中转或派送异常。"}]}
```

字段要求：

- `messages`：必填，数组。
- `role`：只使用 `system`、`user`、`assistant`。
- `content`：不能为空字符串。
- 每条样本至少包含一轮 `user` 和 `assistant`。
- `system` 可选，但建议统一加入邮政客服场景身份设定。

## 5. 推荐项目结构

第三周建议整理为以下结构：

```text
week3/
├── PRD_Qwen2.5_MLX_LoRA微调方案.md
├── mlx_qwen_sft/
│   ├── data/
│   │   ├── train.jsonl
│   │   └── valid.jsonl
│   ├── configs/
│   │   ├── qwen2.5-3b-lora.yaml
│   │   └── qwen2.5-7b-lora.yaml
│   ├── adapters/
│   │   ├── qwen2.5-3b/
│   │   └── qwen2.5-7b/
│   ├── logs/
│   ├── scripts/
│   │   ├── prepare_sft_data.py
│   │   ├── test_inference.py
│   │   └── compare_outputs.py
│   └── README.md
```

## 6. 技术路线

### 6.1 主工具

主工具选择：

- `mlx-lm`

原因：

- Apple 官方生态，适配 Apple Silicon 更稳。
- 支持 LoRA 微调、Adapter 加载、模型生成和权重融合。
- 命令行简单，适合形成可复现实验流程。
- 不需要 CUDA、bitsandbytes 或 NVIDIA 相关依赖。

### 6.2 备选工具

备选工具：

- `mlx-tune`

使用条件：

- 如果后续希望写成更接近 Unsloth 风格的 Python 训练脚本。
- 如果需要更灵活地封装数据加载、训练循环和实验管理。

本阶段建议先用 `mlx-lm` 跑通闭环，再考虑是否补充 `mlx-tune` 版本。

## 7. 模型方案

### 7.1 Qwen2.5 3B

定位：

- 快速实验模型。
- 用于验证数据格式、训练流程、损失下降趋势和基本回复风格。

建议用途：

- 第一轮全流程打通。
- 小样本和中等样本快速试验。
- 调试 prompt、chat template、数据清洗规则。

建议 LoRA 参数：

```yaml
model: "Qwen/Qwen2.5-3B-Instruct"
train: true
data: "./data"
iters: 800
batch_size: 4
learning_rate: 1e-5
grad_checkpoint: true
num_layers: 16
lora_parameters:
  rank: 8
  scale: 16.0
  dropout: 0.05
adapter_path: "./adapters/qwen2.5-3b"
save_every: 100
```

### 7.2 Qwen2.5 7B

定位：

- 主力交付模型。
- 用于最终报告、效果对比和本地部署展示。

建议用途：

- 使用清洗后的完整 SFT 数据。
- 对比微调前后在邮政客服任务上的回答质量。
- 作为后续 Ollama 或本地推理部署候选。

建议 LoRA 参数：

```yaml
model: "Qwen/Qwen2.5-7B-Instruct"
train: true
data: "./data"
iters: 1000
batch_size: 2
learning_rate: 1e-5
grad_checkpoint: true
num_layers: 24
lora_parameters:
  rank: 16
  scale: 32.0
  dropout: 0.05
adapter_path: "./adapters/qwen2.5-7b"
save_every: 100
```

## 8. LoRA / QLoRA 策略

### 8.1 默认策略：LoRA

默认先使用 LoRA，原因是：

- 在 MLX 上路径最直接。
- 配置简单，便于复现。
- 对 3B 和 7B 规模足够实用。
- 训练结果易于保存、加载和融合。

### 8.2 QLoRA 评估策略

QLoRA 不作为第一优先级，但可以作为后续优化方向。

适合考虑 QLoRA 的情况：

- 7B 训练显存或统一内存压力过大。
- 希望进一步提高 batch size。
- 希望降低训练过程内存占用。

注意事项：

- MLX 生态中的量化训练能力和 CUDA 生态的 QLoRA 并不完全等价。
- 本项目文档中应避免把 MLX LoRA 直接写成和 bitsandbytes QLoRA 完全相同。
- 训练报告里应明确说明使用的是 Apple MLX 路线。

## 9. 训练流程

### 9.1 环境安装

建议使用 Python 3.10 或 3.11。

```bash
pip install -U mlx-lm
```

### 9.2 数据准备

进入第三周训练目录后，将已有 SFT 数据转换或复制到：

```text
mlx_qwen_sft/data/train.jsonl
mlx_qwen_sft/data/valid.jsonl
```

如果 `../week2/data/sft_training/` 中已经存在可直接训练的 JSONL 文件，则只需要建立软链接或复制到训练目录。

### 9.3 训练 3B

```bash
cd week3/mlx_qwen_sft
mlx_lm.lora --config configs/qwen2.5-3b-lora.yaml
```

### 9.4 训练 7B

```bash
cd week3/mlx_qwen_sft
mlx_lm.lora --config configs/qwen2.5-7b-lora.yaml
```

### 9.5 推理验证

```bash
mlx_lm.generate \
  --model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path adapters/qwen2.5-7b \
  --max-tokens 512 \
  --prompt "用户咨询 EMS 物流三天没有更新，应该如何回复？"
```

## 10. 评估方案

评估目标不是只证明模型“学到了邮政知识”，还要证明模型没有因为 SFT 变笨、变啰嗦、变机械、变得更容易胡说。微调后的模型必须同时通过领域能力评估和通用能力回归评估。

### 10.1 评估集设计

建议建立四类固定评估集，每次训练 3B 和 7B 都使用同一批题目，保证结果可对比。

```text
eval/
├── postal_domain_eval.jsonl       # 邮政领域专项题
├── general_regression_eval.jsonl  # 通用能力回归题
├── format_eval.jsonl              # JSON / 结构化输出题
└── safety_eval.jsonl              # 幻觉、拒答、政策边界题
```

每类评估集建议先控制在 30 到 100 条，人工可检查，后续再扩充。

### 10.2 邮政领域专项评估

自动评估关注：

- 验证集 loss。
- 训练前后同一 prompt 的输出差异。
- 是否能稳定输出邮政客服风格答案。
- 是否减少泛泛而谈和不相关回答。
- 是否能正确区分 EMS、邮政、快递、包裹、网点、禁限寄、时效等业务场景。

邮政专项题应覆盖：

- EMS 物流长时间不更新。
- 邮政普遍服务和普通快递的边界。
- 禁限寄咨询。
- 国际邮件咨询。
- 网点、改址、退回、签收异常。
- 时效、资费、赔付等容易编造的场景。
- 非邮政问题识别，例如电商售后、商品质量、平台退款。

通过标准：

- 微调后答案的业务相关性应高于原始模型。
- 不允许把明显非邮政问题强行回答成邮政业务。
- 不允许编造具体赔付金额、官方政策或确定时限。
- 不确定时必须建议通过官方渠道、运单号、网点或客服核实。

### 10.3 通用能力回归评估

SFT 后必须检查模型是否退化。不能只看邮政题答得像不像，还要看它是否仍然具备基本通用能力。

通用回归题应覆盖：

- 简单数学推理。
- 中文摘要。
- 信息抽取。
- 多步骤指令遵循。
- 短文本改写。
- 常识问答。
- 简单代码解释。
- 中英文混合理解。

示例题型：

```text
请把下面三句话总结成一句话。
如果一个包裹 3 天走了 240 公里，平均每天走多少公里？
从下面文本中抽取姓名、电话和地址，输出 JSON。
解释这段 Python 代码的作用。
```

通过标准：

- 微调后通用题的人工评分不能明显低于基座模型。
- 不能出现大量邮政客服口吻污染，例如所有问题都强行回答成 EMS 咨询。
- 不能出现明显复读、模板化、无关免责声明。
- 对非邮政任务仍需正常执行用户指令。

### 10.4 结构化输出评估

如果后续模型需要输出分类结果、JSON 或摘要字段，必须单独测试格式稳定性。

评估内容：

- 是否输出合法 JSON。
- 是否包含要求字段。
- 字段类型是否正确。
- 是否夹带 Markdown 代码块。
- 是否在 JSON 外输出解释性废话。

建议字段示例：

```json
{
  "is_postal_related": true,
  "category": "物流查询",
  "confidence": 0.86,
  "reason": "用户询问 EMS 运单长时间未更新"
}
```

通过标准：

- JSON 可解析率不低于原始模型。
- 字段缺失率不能高于原始模型。
- 对格式要求明确的任务，优先保证机器可读。

### 10.5 幻觉与边界评估

邮政客服场景尤其要防止模型编造政策。需要单独准备一批高风险问题。

高风险问题包括：

- 赔偿金额。
- 法定时限。
- 国际禁寄规则。
- 具体网点营业时间。
- 投诉升级路径。
- 身份证、手机号、地址等隐私信息处理。

通过标准：

- 不能凭空给出确定政策。
- 不能要求用户泄露过多个人信息。
- 不能承诺一定赔付、一定送达、一定追回。
- 对需要实时查询的问题，应建议走官方查询或人工客服。

### 10.6 A/B 对比方法

每个评估问题至少生成四组答案：

- 3B 原始模型。
- 3B LoRA 微调模型。
- 7B 原始模型。
- 7B LoRA 微调模型。

建议保存为：

```text
eval_outputs/
├── qwen2.5-3b-base.jsonl
├── qwen2.5-3b-lora.jsonl
├── qwen2.5-7b-base.jsonl
└── qwen2.5-7b-lora.jsonl
```

人工评估时不只看单条答案，而是看同题对比：

- 微调模型是否更懂邮政场景。
- 微调模型是否损失通用能力。
- 7B 微调是否稳定优于 3B 微调。
- LoRA 是否带来真实收益，而不是只改变语气。

### 10.7 人工评分表

建议抽样 50 到 100 条进行人工评估。

评估维度：

- 业务相关性。
- 答案准确性。
- 表达专业性。
- 是否编造政策或承诺。
- 是否有客服可用性。
- 是否能给出清晰下一步处理建议。

建议使用 1 到 5 分评分：

| 维度 | 说明 |
| --- | --- |
| 业务相关性 | 是否准确识别邮政/EMS/快递业务场景 |
| 答案正确性 | 是否符合常识和业务边界 |
| 指令遵循 | 是否按用户要求回答 |
| 通用能力 | 非邮政任务是否仍然正常 |
| 格式稳定性 | JSON 或固定格式是否可解析 |
| 幻觉风险 | 是否编造政策、时限、赔偿或官方结论 |
| 客服可用性 | 是否能作为真实客服回复初稿 |

### 10.8 对比组

至少保留以下对比：

- Qwen2.5-3B-Instruct 原始模型。
- Qwen2.5-3B-Instruct LoRA 微调后。
- Qwen2.5-7B-Instruct 原始模型。
- Qwen2.5-7B-Instruct LoRA 微调后。

### 10.9 最低验收阈值

模型只有同时满足以下条件，才算 SFT 成功：

- 邮政领域专项评估平均分高于对应基座模型。
- 通用能力回归评估不能明显下降。
- 非邮政问题不能被大量误导成邮政客服问题。
- JSON / 结构化输出可解析率不能低于基座模型。
- 高风险政策问题不能出现严重编造。
- 7B 微调模型应作为主交付候选，除非 3B 在速度和效果之间明显更适合展示。

如果模型领域能力提升，但通用能力明显下降，则不能直接作为最终模型，只能作为过拟合实验样本保留。

## 11. 输出物

本阶段完成后应产出：

- `configs/qwen2.5-3b-lora.yaml`
- `configs/qwen2.5-7b-lora.yaml`
- `data/train.jsonl`
- `data/valid.jsonl`
- `adapters/qwen2.5-3b/`
- `adapters/qwen2.5-7b/`
- 训练日志
- 推理对比样例
- 微调前后效果总结
- README 运行说明

## 12. 权重融合与部署

训练完成后，可使用 `mlx_lm.fuse` 将 LoRA Adapter 融合到基座模型中。

示例：

```bash
mlx_lm.fuse \
  --model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path adapters/qwen2.5-7b \
  --save-path fused/qwen2.5-7b-postal
```

后续如果需要接入 Ollama，应再评估 GGUF 转换流程。部署文档中要明确区分：

- MLX 本地推理。
- 融合后的 MLX 模型。
- GGUF / Ollama 部署版本。

## 13. 风险与应对

### 13.1 数据质量不足

风险：

- 原始客服摘要不一定天然适合 SFT。
- 数据中可能存在泛物流、电商、订单售后等非严格邮政样本。

应对：

- 复用第二版中的 regex 与大模型标签结果做过滤。
- 优先训练严格邮政/EMS相关样本。
- 保留低质量样本清洗日志。

### 13.2 模型学到错误客服口径

风险：

- 模型可能生成过度承诺。
- 模型可能编造具体赔付、时限或政策。

应对：

- 在 system prompt 中加入“不能编造政策和承诺”的约束。
- 人工评估中单独检查政策类回答。
- 对不确定问题要求模型建议联系官方渠道或网点核实。

### 13.3 训练参数过大

风险：

- batch size、num_layers 或 rank 过大导致训练速度慢或内存压力高。

应对：

- 先用 3B 小步数跑通。
- 7B 从保守参数开始。
- 每 100 步保存一次 Adapter，支持中断后恢复。

## 14. 里程碑

### M1：数据准备

- 确认 `sft_training` 数据格式。
- 生成 `train.jsonl` 和 `valid.jsonl`。
- 完成 20 条样本人工抽查。

### M2：3B 流程打通

- 完成 Qwen2.5 3B LoRA 微调。
- 完成微调前后推理对比。
- 记录训练命令、耗时、loss 和样例。

### M3：7B 主模型训练

- 完成 Qwen2.5 7B LoRA 微调。
- 完成验证集和人工评估。
- 选出最终 Adapter。

### M4：融合与展示

- 完成 Adapter 加载推理。
- 可选完成模型融合。
- 输出 README 和最终实验总结。

## 15. 验收标准

满足以下条件即可认为第三周微调阶段完成：

- 3B 和 7B 至少各完成一次可复现 LoRA 微调。
- 所有训练命令、配置和数据路径均使用相对路径。
- 微调前后至少各保留 10 条同题对比样例。
- 7B 微调后在邮政客服场景中明显优于原始模型。
- Adapter 权重、配置文件、训练日志和 README 齐全。
- 文档中清楚说明 MLX、LoRA、数据来源、训练参数和限制。
