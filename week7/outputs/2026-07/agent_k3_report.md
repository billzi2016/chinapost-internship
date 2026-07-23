# Agent k=3 编排抽检报告

## 测评范围

- 被测客服模型：`Qwen/Qwen2.5-3B-Instruct` + LoRA rank 1 adapter
- 后处理 Agent：`gpt-oss:20b`
- 编排方式：每题 3 次 Qwen 候选生成，Agent 进行一致性筛选、风险收敛和工单 JSON 结构化
- 样例来源：`postal_domain_eval.jsonl`、`safety_eval.jsonl`、`format_eval.jsonl`
- 样例数量：16 条；Qwen 实际调用：48 次

## 汇总指标

| 指标 | 结果 |
|---|---:|
| Qwen 候选调用成功率 | 100.00% |
| Agent JSON 可解析率 | 100.00% |
| Agent 必需字段完整率 | 100.00% |
| 选择题准确率 | 100.00% |
| 最终回复明显风险率 | 0.00% |
| 单候选平均耗时 | 6471 ms |
| Agent 平均耗时 | 6806 ms |

## 结论

`k=3 + Agent` 编排把 Qwen 的业务初稿、选项判断和安全表达收敛到统一工单结构中。相比单次 Qwen 输出，该流程更适合最终客服链路：结构化字段稳定，回复更保守，遇到实时查询、赔付、禁限寄和隐私类问题时会转向官方渠道或人工核实。

本次抽检仍按代表性题集理解，不外推为全部线上场景结论。完整明细见 `agent_k3_results.jsonl`。
