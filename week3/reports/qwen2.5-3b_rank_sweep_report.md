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
../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/
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

横向对比图：

![Rank comparison](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/rank_comparison.jpg)

## 3. 横向结果

| Rank | Best Step | Best Score | Final Score | JSON Valid | JSON Keys | Safety Risk | Postal Terms | Next Steps |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 300 | 3.1188 | 2.8375 | 1.0000 | 0.3333 | 0.0000 | 2.1250 | 1.5000 |
| 2 | 100 | 3.0750 | 0.7375 | 1.0000 | 0.3333 | 0.0000 | 2.0000 | 1.3750 |
| 4 | 100 | 3.1188 | 2.7813 | 1.0000 | 0.3333 | 0.0000 | 2.1250 | 1.5000 |
| 8 | 100 | 3.0438 | 0.8750 | 1.0000 | 0.3333 | 0.0000 | 2.1250 | 1.1250 |
| 16 | 200 | 0.7938 | 0.7563 | 1.0000 | 0.3333 | 0.0000 | 1.1250 | 0.6250 |
| 32 | 700 | 1.6396 | -1.8313 | 0.6667 | 0.0000 | 0.0000 | 0.8750 | 0.8750 |

从结果看，rank 并不是越大越好。rank 1 和 rank 4 的 best score 并列最高，且 final score 也明显高于其他 rank。rank 2、8、16 虽然 early step 有一定效果，但最终分数下降明显。rank 32 的训练 loss 可能继续下降，但评估指标反而明显变差，属于典型的 SFT 过拟合或行为漂移风险。

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

rank 1 的 best step 出现在 300 step，best score 为 3.1188，final score 为 2.8375。它的优势是训练曲线相对平稳，最终没有出现明显邮政话术污染，JSON 可解析率保持为 1.0，安全风险为 0。

不足是 JSON 必需字段完整率只有 0.3333，说明模型虽然能输出 JSON，但 schema 对齐不够稳定。这个问题不是 rank 1 独有，几乎所有 rank 都存在。

训练图：

![Rank 1 dashboard](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/qwen2.5-3b-lora-r1_training_dashboard.jpg)

结论：rank 1 是本次实验中最稳的方案之一。它参数最少、权重最小、训练风险低，适合做轻量基线。

### Rank 2

rank 2 的 best step 在 100 step，best score 为 3.0750，但 final score 降到 0.7375。说明它在早期已经学到一部分邮政业务表达，但继续训练后出现明显退化。

final 阶段的最大邮政污染率为 1，说明模型可能把邮政客服话术带到了通用任务中。虽然 JSON 可解析率和安全风险没有明显问题，但泛化表现不如 rank 1 和 rank 4。

训练图：

![Rank 2 dashboard](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/qwen2.5-3b-lora-r2_training_dashboard.jpg)

结论：rank 2 不适合作为最终方案。如果使用 rank 2，应该只取 100 step 的 best adapter，不应使用最终 800 step 的 adapter。

### Rank 4

rank 4 的 best step 在 100 step，best score 为 3.1188，与 rank 1 并列最高。final score 为 2.7813，略低于 rank 1，但仍然明显优于 rank 2、8、16、32。

rank 4 的特点是早期收敛很快，100 step 就达到最佳点。它的邮政业务命中和下一步处理建议命中与 rank 1 持平，JSON 可解析率为 1.0，安全风险为 0，final 阶段也没有出现最大污染率为 1 的问题。

训练图：

![Rank 4 dashboard](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/qwen2.5-3b-lora-r4_training_dashboard.jpg)

结论：rank 4 是本次实验最推荐的折中方案。它比 rank 1 有更强的表达容量，但还没有像高 rank 那样明显引入不稳定。

### Rank 8

rank 8 的 best step 在 100 step，best score 为 3.0438，和 rank 1、rank 4 接近。但 final score 下降到 0.8750，后期退化明显。

它的邮政业务词命中还可以，但下一步处理建议命中低于 rank 1 和 rank 4。final 阶段也出现最大污染率为 1，说明继续训练后模型可能把邮政场景表达带到了不该出现的任务中。

训练图：

![Rank 8 dashboard](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/qwen2.5-3b-lora-r8_training_dashboard.jpg)

结论：rank 8 可以作为扩展容量的候选，但需要更严格的 early stopping。目前这组实验里不如 rank 4 稳。

### Rank 16

rank 16 的 best step 在 200 step，best score 只有 0.7938，final score 为 0.7563。它的邮政业务命中和下一步建议命中都明显低于 rank 1、rank 4 和 rank 8。

rank 16 的问题不是简单的训练不足，而是高 rank 带来的有效收益没有体现出来。它在 JSON 可解析率和安全风险上没有明显崩坏，但业务指标和综合分都偏低，并且 final 阶段也出现了通用任务污染信号。

训练图：

![Rank 16 dashboard](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/qwen2.5-3b-lora-r16_training_dashboard.jpg)

结论：rank 16 当前不建议继续作为主线。若后续要尝试，需要重新调整学习率、训练步数或数据配比。

### Rank 32

rank 32 的 best step 出现在 700 step，best score 为 1.6396，但 final score 降到 -1.8313。它是本次实验里退化最明显的配置。

更关键的是，rank 32 的 JSON 可解析率下降到 0.6667，JSON 必需字段完整率为 0，final 阶段 JSON 指标进一步变成 0。说明高 rank 不仅没有稳定提升邮政能力，反而破坏了格式输出能力。

训练图：

![Rank 32 dashboard](../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/plots/qwen2.5-3b-lora-r32_training_dashboard.jpg)

结论：rank 32 不适合作为本项目的 3B 微调配置。它的容量过高，容易带来格式退化和行为漂移。

## 5. 主要结论

第一，3B 模型在当前数据和训练设置下，更适合小 rank LoRA。rank 1 和 rank 4 的综合表现最好，说明邮政业务 SFT 并不需要过大的 LoRA 容量。

第二，rank 4 是当前推荐配置。它在 100 step 就达到最高综合分，邮政业务命中较好，JSON 可解析率和安全风险也稳定。相比 rank 1，rank 4 保留了更多表达容量；相比 rank 8 以上，它的退化风险更低。

第三，高 rank 不等于更好。rank 16 和 rank 32 的表现说明，当 LoRA 容量过大时，模型可能更容易记住训练集风格，而不是稳定学习任务边界。rank 32 尤其明显，后期 JSON 能力和 final score 都出现严重下降。

第四，JSON schema 对齐仍然是短板。大多数 rank 的 JSON 可解析率较高，但 `json_keys` 长期只有 0.3333，说明模型能输出 JSON 结构，却不能稳定包含全部必需字段。后续如果目标是结构化输出，应该增加格式样本、强化字段约束，或者在推理阶段接入更强的 JSON 修复/校验节点。

第五，自动评估和 best adapter 保留机制是必要的。rank 2、8、32 都出现了 best step 明显早于 final step 的情况。如果只看最后一个 adapter，很容易选到已经退化的模型。

## 6. 推荐方案

当前建议使用：

```text
Qwen2.5-3B-Instruct + LoRA rank 4
```

推荐使用的 adapter：

```text
../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/rank_4/best_adapter/qwen2.5-3b-lora-r4/
```

rank 1 可以作为轻量备选：

```text
../mlx_qwen_sft/runs/20260623_224112_3b_rank_sweep/rank_1/best_adapter/qwen2.5-3b-lora-r1/
```

不建议使用 rank 16 和 rank 32 作为当前 3B 主配置。

## 7. 后续改进方向

1. 增加 JSON 格式专项数据，重点覆盖必需字段缺失、字段名不一致、嵌套结构错误等问题。
2. 对 rank 4 做更细训练步数实验，例如 50、100、150、200 step，确认最佳点是否稳定在早期。
3. 增加 base 模型对照评估，明确 SFT 相比原始 Qwen2.5-3B-Instruct 的提升幅度。
4. 在最终流程中保留 GPT-OSS 或规则校验节点，用于结构化 JSON 的二次校验和修复。
5. 对 7B 重复同样的 rank sweep，判断更大基座模型是否可以承受更高 rank。
