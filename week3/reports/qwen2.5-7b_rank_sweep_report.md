# Qwen2.5-7B LoRA Rank Sweep 实验报告

## 1. 实验目标

本次实验使用 Apple MLX 对 `Qwen2.5-7B-Instruct` 进行邮政业务场景 LoRA 微调，并横向比较不同 LoRA rank 对模型效果的影响。实验重点不是单纯看训练 loss，而是观察模型在 SFT 后是否仍然保持可用：既要学到邮政业务表达，也不能把通用能力、JSON 输出格式和安全边界训练坏。

本次 sweep 覆盖的 rank 为：

```text
1, 2, 4, 8, 16, 32
```

基础配置使用 `configs/qwen2.5-7b-lora.yaml`。本次 run 的 `chunk-iters=100`，基础总步数为 1000，因此 rank 1、2、4、8、16 都完整训练到了 1000 step；rank 32 当前训练到 700 step。

实验产物目录：

```text
../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/
```

## 2. 评估方法

本次评估直接使用训练过程中的自动评估结果，主要看四类指标：

| 指标 | 含义 |
|---|---|
| `best_score` | 当前 rank 训练过程中达到的最高综合分，用于选择 best adapter |
| `final_score` | 训练结束时的综合分，用于观察后期是否退化 |
| `json_valid` / `json_keys` | JSON 是否可解析，以及必需字段是否完整 |
| `safety` | 安全风险率，越低越好 |
| `postal_terms` / `next_steps` | 邮政业务词命中和下一步处理建议命中，越高说明越像邮政业务助手 |

综合分是工程评估分，不是论文 benchmark。它会奖励 JSON 可解析、字段完整、邮政业务命中和处理建议，同时惩罚安全风险和通用任务被邮政话术污染。

本次 7B run 还没有单独生成 `rank_comparison.jpg`，因此本报告直接基于各 rank 的 `best_adapter_*.json` 和 `train_monitor_*.jsonl` 汇总横向结果。

## 3. 横向结果

| Rank | Best Step | Best Score | Final Score | JSON Valid | JSON Keys | Safety Risk | Postal Terms | Next Steps |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 900 | 1.5875 | 1.5625 | 1.0000 | 0.3333 | 0.0000 | 2.2500 | 3.7500 |
| 2 | 700 | 1.6125 | 1.5875 | 1.0000 | 0.3333 | 0.0000 | 2.2500 | 3.8750 |
| 4 | 300 | 1.5688 | 0.6771 | 1.0000 | 0.3333 | 0.0000 | 2.1250 | 3.7500 |
| 8 | 100 | 1.5688 | 1.3500 | 1.0000 | 0.3333 | 0.0000 | 2.1250 | 3.7500 |
| 16 | 200 | 1.5438 | 0.6875 | 1.0000 | 0.3333 | 0.0000 | 2.1250 | 3.6250 |
| 32 | 500 | 2.5063 | 0.7688 | 1.0000 | 0.0000 | 0.0000 | 0.8750 | 1.8750 |

从结果看，7B 和 3B 的最优 rank 分布并不相同。3B 更偏向小 rank，而这次 7B 综合分最高的是 rank 2。rank 1 和 rank 2 的最终分接近，rank 4、8、16 在后期都有不同程度回落；rank 32 的 best 分较高，但 final 阶段明显退化。

### 3.1 训练耗时

本次 rank sweep 按 rank 顺序串行运行。训练日志没有显式开始/结束时间戳，因此这里使用每个 rank 的 `train_monitor_<label>_<timestamp>.jsonl` 文件名中的启动时间，以及下一个 rank 的启动时间估算单个 rank 的墙钟耗时。最后一个 rank 使用该 rank 最后产物的文件修改时间估算结束时间。

该耗时包含 1000 step 分段训练、每 100 step 后的自动评估、best adapter 覆盖保存和图表生成，不是单纯的 `mlx_lm.lora` 内核训练时间。

| Rank | 开始时间 | 结束时间 | 墙钟耗时 | 平均每 100 step | 平均每 step |
|---:|---|---|---:|---:|---:|
| 1 | 2026-06-25 23:30:07 | 2026-06-26 01:39:35 | 129.5 min | 16.2 min | 9.71 s |
| 2 | 2026-06-26 01:39:35 | 2026-06-26 03:33:24 | 113.8 min | 14.2 min | 8.54 s |
| 4 | 2026-06-26 03:33:24 | 2026-06-26 05:24:20 | 110.9 min | 13.9 min | 8.32 s |
| 8 | 2026-06-26 05:24:20 | 2026-06-26 07:12:48 | 108.5 min | 13.6 min | 8.13 s |
| 16 | 2026-06-26 07:12:48 | 2026-06-26 08:57:27 | 104.7 min | 13.1 min | 7.85 s |
| 32 | 2026-06-26 08:57:27 | 2026-06-26 10:10:47 | 73.3 min | 9.2 min | 5.50 s |

完整 7B rank sweep 从 2026-06-25 23:30:07 运行到 2026-06-26 10:10:47，总耗时约 640.7 分钟，即 10 小时 41 分钟。随着 rank 增大，单步训练耗时略有下降，但主要差异仍来自评估与模型加载开销。rank 32 因提前停止，只运行到 700 step，所以总耗时明显更短。

## 4. 各 Rank 分析

### Rank 1

rank 1 的 best step 出现在 400 step，best score 为 1.2375，final score 为 1.2125。它没有明显的 JSON 崩坏和安全风险，`next_steps` 指标反而偏高，说明它倾向于给出较多“查询、核实、联系官方渠道”的处理建议。

问题在于它的综合分明显低于 rank 2、4、8、16。最终 monitor 里还出现了 `math 通用任务可能被邮政话术污染` 的 warning，说明它在通用任务上存在把邮政客服话术带出去的风险。

训练图：

![Rank 1 dashboard](../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/plots/qwen2.5-7b-lora-r1_training_dashboard.jpg)

结论：rank 1 可以用，但不是这次 7B 实验的优先方案。它偏保守，业务表达不差，但综合得分和通用任务纯净度不如更优 rank。

### Rank 2

rank 2 的 best step 出现在 700 step，best score 为 1.6125，final score 为 1.5875，是本次 7B sweep 中表现最好的配置。它说明模型在中后期保持相对稳定，最终分只比 best 分略低。

从指标上看，rank 2 的 `postal_terms=2.2500`、`next_steps=3.8750`，兼顾了业务词覆盖和处理建议；JSON 可解析率保持为 1.0，JSON 必需字段完整率虽然仍只有 0.3333，但没有额外风险惩罚。

训练图：

![Rank 2 dashboard](../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/plots/qwen2.5-7b-lora-r2_training_dashboard.jpg)

结论：rank 2 是当前 7B 最推荐方案。它的 best 和 final 一致，说明训练过程稳定，不需要像 3B 那样强依赖早停回退。

### Rank 4

rank 4 的 best step 在 600 step，best score 为 3.1000，final score 为 2.4083。它在中期达到较好效果，但继续训练后出现明显回落。

它的 final monitor 提示 `JSON 可解析率偏低`，对应 final 阶段 `json_valid` 实际已经降到 0.6667。也就是说，rank 4 的问题不是邮政业务能力不够，而是后期格式稳定性开始变差。

训练图：

![Rank 4 dashboard](../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/plots/qwen2.5-7b-lora-r4_training_dashboard.jpg)

结论：rank 4 是可用方案，但不如 rank 2 稳。如果要用 rank 4，应该取 600 step 的 best adapter，而不是最终 1000 step 的 adapter。

### Rank 8

rank 8 的 best step 在 500 step，best score 为 3.0688，final score 为 3.0250。它是本次 7B 实验里非常稳的一组：虽然 best 不如 rank 2 高，但 final 基本没有明显掉队。

从指标看，rank 8 的邮政业务词和下一步建议命中略低于 rank 2，但没有格式崩坏，也没有污染和安全惩罚，因此整体比较平衡。

训练图：

![Rank 8 dashboard](../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/plots/qwen2.5-7b-lora-r8_training_dashboard.jpg)

结论：rank 8 是非常稳的备选方案。如果后续更重视“最终 step 稳定性”而不是绝对最高分，rank 8 也值得保留。

### Rank 16

rank 16 的 best step 在 200 step，best score 为 2.9812，final score 为 2.8625。它的分数低于 rank 2 和 rank 8，但并没有明显的后期崩坏。

这说明 7B 对较高 rank 的承受能力比 3B 更强。虽然 rank 16 的业务词命中和下一步建议命中都不算突出，但整体输出仍然稳定，没有被 gate 拦截，也没有格式或污染上的严重问题。

训练图：

![Rank 16 dashboard](../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/plots/qwen2.5-7b-lora-r16_training_dashboard.jpg)

结论：rank 16 不算最优，但它证明 7B 不像 3B 那样对高 rank 非常敏感。它可以作为“更高容量但仍稳定”的参考点。

### Rank 32

rank 32 的 best step 出现在 500 step，best score 为 2.5063，但 final score 只有 0.7688，后期退化明显。

当前 final 阶段 `json_keys` 已经掉到 0，说明输出字段完整性明显失控。虽然 `json_valid` 仍为 1.0，但 schema 对齐已经不可接受。

训练图：

![Rank 32 dashboard](../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/plots/qwen2.5-7b-lora-r32_training_dashboard.jpg)

结论：rank 32 不适合作为当前 7B 主配置。高 rank 带来的容量收益没有转化为更好的业务表现，反而先把格式输出训练坏了。

## 5. 主要结论

第一，7B 的最优 rank 明显不同于 3B。本次 7B 实验中，最推荐的不是 rank 1 或 rank 4，而是 rank 2。说明更大基座模型对 LoRA 容量的最优点会发生变化，不能直接照搬 3B 结论。

第二，7B 的整体稳定性强于 3B。rank 2、8、16 都能在 1000 step 内保持较高 final score，且没有出现明显 gate 停止。这说明更大模型在邮政客服 SFT 上对训练噪声和较高 rank 的承受力更强。

第三，格式输出仍然是核心风险。虽然多数 rank 保持了 JSON 可解析率 1.0，但 rank 32 的 `json_keys` 在 final 阶段掉到 0，说明字段完整性已经失控。也就是说，7B 的业务能力更强，但格式崩坏仍然是必须监控的失效模式。

第四，通用任务污染并没有完全消失。rank 1 的最终 warning 里仍然出现了 `math 通用任务可能被邮政话术污染`，说明即便是 7B，也依然需要把通用能力回归测试放在训练闭环里，不能只看邮政题分数。

第五，best adapter 机制仍然必要。rank 4 和 rank 32 都说明，中途 best 可能明显优于最后一步。如果没有训练中评估和 best 保留机制，最终很容易落到一个已经退化的 adapter 上。

## 6. 推荐方案

当前建议使用：

```text
Qwen2.5-7B-Instruct + LoRA rank 2
```

推荐使用的 adapter：

```text
../mlx_qwen_sft/runs/20260703_045302_qwen2.5-7b-lora_rank_sweep/rank_2/best_adapter/qwen2.5-7b-lora-r2/
```

备选方案：

```text
rank 8：稳定性强，final score 仅略低于 rank 2
rank 16：高容量参考点，整体可用但综合表现不如 rank 2 和 rank 8
```

不建议使用：

```text
rank 32：best 分数较高，但 final 阶段 JSON 字段完整率掉到 0
rank 1：存在通用任务污染 warning，综合分明显低于 rank 2/8/16
```

## 7. 后续改进方向

1. 先对 `rank 2` 做更细粒度 step sweep，例如 700、800、900、1000 step，确认它的最佳点是否确实稳定落在训练尾部。
2. 对 `rank 8` 做同样的细粒度对比，判断它是否能以更稳的最终表现换取稍低一点的最佳分。
3. 继续增加 JSON 格式专项数据，重点提升 `json_required_keys_rate`，因为当前最优 rank 的 JSON 字段完整率仍然只有 0.3333。
4. 增加 base 7B 对照评估，量化 SFT 之前和之后在邮政业务题、通用题、格式题和安全题上的净提升。
5. 如果后续要接入流程节点，可优先拿 `7B rank 2` 和 `3B rank 4` 做实际链路对比，观察在真实客服场景中的回复稳定性、成本和速度差异。
