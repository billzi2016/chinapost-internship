# Qwen2.5-3B LoRA Rank Sweep 实验报告

## 1. 实验目标

本次实验使用 Apple MLX 对 `Qwen2.5-3B-Instruct` 进行邮政业务场景 LoRA 微调，并横向比较不同 LoRA rank 对模型效果的影响。实验重点不是单纯降低训练 loss，而是判断模型在 SFT 后是否仍然保持可用：既要学到邮政业务表达，也不能把通用能力、JSON 输出格式和安全边界训练坏。

本次 sweep 覆盖的 rank 为：

```text
1, 2, 4, 8, 16, 32
```

每个 rank 训练到 800 step，每 100 step 做一次自动评估。训练过程中只保留该 rank 的 best adapter，避免保存大量中间权重。

实验产物目录：

```text
../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/
```

## 2. 评估方法

本次评估采用训练过程中的自动评估结果，主要看四类指标：

| 指标 | 含义 |
|---|---|
| `best_score` | 当前 rank 训练过程中达到的最高综合分，用于选择 best adapter |
| `final_score` | 800 step 结束时的综合分，用于观察后期是否退化 |
| `json_valid` / `json_keys` | JSON 是否可解析，以及必需字段是否完整 |
| `safety` | 安全风险率，越低越好 |
| `postal_terms` / `next_steps` | 邮政业务词命中和下一步处理建议命中，越高说明越像邮政业务助手 |

综合分是工程评估分，不是论文 benchmark。它会奖励 JSON 可解析、字段完整、邮政业务命中和处理建议，同时惩罚安全风险和通用任务被邮政话术污染。

本次重新运行后，`plots/` 目录保留的是每个 rank 的 `training_dashboard` 和 `latest_output_length` 图，没有再保留单独的 `rank_comparison.jpg` 汇总图。

## 3. 横向结果

| Rank | Best Step | Best Score | Final Score | JSON Valid | JSON Keys | Safety Risk | Postal Terms | Next Steps |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 500 | 3.6313 | 3.4000 | 1.0000 | 0.3333 | 0.0000 | 2.8750 | 3.5000 |
| 2 | 400 | 3.4062 | 2.6875 | 1.0000 | 0.3333 | 0.0000 | 1.8750 | 3.1250 |
| 4 | 200 | 3.2750 | 2.6500 | 1.0000 | 0.3333 | 0.0000 | 1.5000 | 2.7500 |
| 8 | 100 | 3.4000 | 2.6750 | 1.0000 | 0.3333 | 0.0000 | 2.0000 | 3.0000 |
| 16 | 400 | 3.1125 | 2.5938 | 1.0000 | 0.3333 | 0.0000 | 1.2500 | 2.1250 |
| 32 | 500 | 2.9062 | 0.3875 | 1.0000 | 0.3333 | 0.0000 | 0.8750 | 1.3750 |

从这次重跑结果看，rank 并不是越大越好，但最优点已经从旧结论里的 rank 4 转到了 rank 1。rank 1 拿到本轮最高 `best_score` 和最高 `final_score`，并且后期没有明显崩坏。rank 2、8、16 也都比上一轮稳定得多，不再是早期有收益、后期大幅退化的状态。rank 32 虽然较上一轮明显改善，但 800 step 时 JSON 仍然完全不可解析，仍然属于高风险配置。

### 3.1 训练耗时

本次 rank sweep 是按 rank 顺序串行运行的。训练日志本身没有写入显式开始和结束时间戳，因此这里使用各 rank 日志目录名中的启动时间，以及下一个 rank 的启动时间估算单个 rank 的墙钟耗时。最后一个 rank 没有下一个启动时间，使用该 rank 最后产物的文件修改时间估算结束时间。

该耗时包含 800 step 分段训练、每 100 step 后的自动评估、best adapter 覆盖保存和图表生成，不是单纯的 `mlx_lm.lora` 内核训练时间。

| Rank | 开始时间 | 结束时间 | 墙钟耗时 | 平均每 100 step | 平均每 step |
|---:|---|---|---:|---:|---:|
| 1 | 2026-06-23 22:41:12 | 2026-06-23 23:35:49 | 54.6 min | 6.8 min | 4.10 s |
| 2 | 2026-06-23 23:35:49 | 2026-06-24 00:29:12 | 53.4 min | 6.7 min | 4.00 s |
| 4 | 2026-06-24 00:29:12 | 2026-06-24 01:22:07 | 52.9 min | 6.6 min | 3.97 s |
| 8 | 2026-06-24 01:22:07 | 2026-06-24 02:15:07 | 53.0 min | 6.6 min | 3.98 s |
| 16 | 2026-06-24 02:15:07 | 2026-06-24 03:07:20 | 52.2 min | 6.5 min | 3.92 s |
| 32 | 2026-06-24 03:07:20 | 2026-06-24 03:57:47 | 50.5 min | 6.3 min | 3.79 s |

完整 3B rank sweep 从 2026-06-23 22:41:12 运行到 2026-06-24 03:57:47，总耗时约 316.6 分钟，即 5 小时 16 分钟。不同 rank 的耗时差异不大，说明本次实验的主要成本来自固定的训练步数、评估频率和模型加载/生成开销，而不是 LoRA rank 本身。

## 4. 各 Rank 分析

### Rank 1

rank 1 的 best step 出现在 500 step，best score 为 3.6313，final score 为 3.4000。它不只是轻量，而且已经成为这次 sweep 的综合最优配置。best 阶段和 final 阶段都保持了较高综合分，说明这一轮 rank 1 的稳定性明显强于上一版结果。

不足是 JSON 必需字段完整率只有 0.3333，说明模型虽然能输出 JSON，但 schema 对齐不够稳定。这个问题不是 rank 1 独有，几乎所有 rank 都存在。

训练图：

![Rank 1 dashboard](../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/plots/qwen2.5-3b-lora-r1_training_dashboard.jpg)

结论：rank 1 不再只是轻量基线，而是本轮最推荐的主配置。它参数最少、权重最小，但综合分、后期稳定性和格式表现都最好。

### Rank 2

rank 2 的 best step 在 400 step，best score 为 3.4063，final score 为 2.6875。相比上一轮 final score 只有 0.7375，这次 rank 2 的稳定性改善非常明显，后期没有再出现大幅崩坏。

不足是 final 阶段 `safety risk` 为 0.2，仍然高于 rank 1、4、8、32 的 0，因此它虽然综合分提升很大，但安全边界还不如 rank 1 稳。

训练图：

![Rank 2 dashboard](../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/plots/qwen2.5-3b-lora-r2_training_dashboard.jpg)

结论：rank 2 已经从“明显退化”变成“可用候选”。如果你想在保持小容量的同时提高一些表达能力，它可以作为 rank 1 之后的备选，但不是首推。

### Rank 4

rank 4 的 best step 在 200 step，best score 为 3.2750，final score 为 2.6500。它仍然是一个可用配置，但已经不再像上一轮那样与 rank 1 并列最优。

更关键的是，这一轮 rank 4 在 final 阶段的邮政业务词命中和下一步建议命中明显偏低，说明它虽然分数还可以，但业务向表达保持得不如 rank 1、2、16 稳。

训练图：

![Rank 4 dashboard](../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/plots/qwen2.5-3b-lora-r4_training_dashboard.jpg)

结论：rank 4 现在更适合看作中等容量的参考点，而不是第一推荐。它没有严重崩坏，但综合收益已经被 rank 1、2、8 超过。

### Rank 8

rank 8 的 best step 在 100 step，best score 为 3.4000，final score 为 2.6750。和上一轮 final score 只有 0.8750 相比，这次 rank 8 的后期稳定性提升非常明显。

不过它的 final 阶段邮政业务词命中和下一步建议命中仍然偏低，说明它的综合分更多来自格式稳定和通用项修复，而不是业务表达特别强。

训练图：

![Rank 8 dashboard](../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/plots/qwen2.5-3b-lora-r8_training_dashboard.jpg)

结论：rank 8 已经比上一轮成熟很多，可以作为中高容量备选，但从综合稳定性和业务表达平衡来看，仍不如 rank 1。

### Rank 16

rank 16 的 best step 在 400 step，best score 为 3.1125，final score 为 2.5938。相比上一轮几乎失败的状态，这一轮 rank 16 提升非常明显，已经进入可用区间。

它的问题变成了“有进步但不够稳”。final 阶段 `safety risk` 为 0.2，通用项表现也不如 rank 1、2，说明高 rank 的收益开始出现，但副作用仍然偏大。

训练图：

![Rank 16 dashboard](../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/plots/qwen2.5-3b-lora-r16_training_dashboard.jpg)

结论：rank 16 不再是“明显不建议”的配置，但仍不适合作为主线首选。它说明这次重跑把高 rank 训练稳定性拉回来了，但还没好到值得替代 rank 1。

### Rank 32

rank 32 的 best step 出现在 500 step，best score 为 2.9063，final score 为 0.3875。相比上一轮已经大幅改善，但它仍然是本轮最不稳定的配置。

更关键的是，rank 32 在 800 step 时 `json_valid_rate = 0`、`json_required_keys_rate = 0`，说明 final 阶段格式能力仍然完全崩坏。也就是说，它的 best adapter 可以比上一轮好一些，但最后一步模型依旧不可信。

训练图：

![Rank 32 dashboard](../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/plots/qwen2.5-3b-lora-r32_training_dashboard.jpg)

结论：rank 32 不适合作为本项目的 3B 微调配置。它的容量过高，容易带来格式退化和行为漂移。

## 5. 主要结论

第一，这次重跑后，3B 模型的最优配置已经从旧结论里的 rank 4 转成了 rank 1。rank 1 同时拿到最高 `best_score` 和最高 `final_score`，说明在当前数据和训练设置下，小 rank LoRA 仍然最合适。

第二，这次 rank 2、8、16 都比上一轮显著改善，尤其是 rank 2 和 rank 8，不再是典型“早期好、后期崩”的配置。这说明训练流程或数据状态较上一轮更稳定，高 rank 以外的中间 rank 开始有了可比较的实际价值。

第三，高 rank 仍然不等于更好。rank 16 虽然已经明显改善，但 rank 32 在 final 阶段仍然出现 JSON 完全不可解析的问题，因此高容量配置的后期退化风险依旧存在。

第四，JSON schema 对齐仍然是短板。大多数 rank 的 JSON 可解析率较高，但 `json_keys` 长期只有 0.3333，说明模型能输出 JSON 结构，却不能稳定包含全部必需字段。后续如果目标是结构化输出，应该增加格式样本、强化字段约束，或者在推理阶段接入更强的 JSON 修复/校验节点。

第五，自动评估和 best adapter 保留机制是必要的。rank 2、8、32 都出现了 best step 明显早于 final step 的情况。如果只看最后一个 adapter，很容易选到已经退化的模型。

## 6. 推荐方案

当前建议使用：

```text
Qwen2.5-3B-Instruct + LoRA rank 1
```

推荐使用的 adapter：

```text
../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/rank_1/best_adapter/qwen2.5-3b-lora-r1/
```

rank 2 可以作为这轮更强的备选：

```text
../mlx_qwen_sft/runs/20260703_021130_qwen2.5-3b-lora_rank_sweep/rank_2/best_adapter/qwen2.5-3b-lora-r2/
```

rank 4 可作为中等容量参考配置；rank 16 暂不作为首选；rank 32 仍不建议作为当前 3B 主配置。

## 7. 后续改进方向

1. 增加 JSON 格式专项数据，重点覆盖必需字段缺失、字段名不一致、嵌套结构错误等问题。
2. 对 rank 1 做更细训练步数实验，例如 400、500、600 step，确认最佳点是否稳定在中后期。
3. 增加 base 模型对照评估，明确 SFT 相比原始 Qwen2.5-3B-Instruct 的提升幅度。
4. 在最终流程中保留 GPT-OSS 或规则校验节点，用于结构化 JSON 的二次校验和修复。
5. 对 7B 重复同样的 rank sweep，判断更大基座模型是否可以承受更高 rank。
