# Week 6：SFT 微服务、LoRA 对照与人工验证

本周目标是把 Qwen2.5 3B/7B 的 LoRA 微调结果服务化，并和 base 模型形成可对照的人工验证路径。

## 主要工作

- 将 `week3/microservice` 从单文件 FastAPI 拆成 `src/` 内部模块，只保留外部入口。
- 拆分 3B 和 7B 配置，并分别指向当前最优 LoRA adapter。
- 提供 3B base、7B base、3B LoRA、7B LoRA 四类启动脚本。
- 将 `max_tokens` 调整到更适合投诉处理、流程说明和长解释的长度。
- 增加人工多轮对话验证脚本，支持 stream 模式。
- 记录每次完整调用的输入、输出、耗时和配置，便于复盘 SFT 是否真的挂载。

## 当前产物

- `week3/microservice/src/`：FastAPI 微服务核心代码。
- `week3/microservice/config_3b.yaml`：3B 服务配置。
- `week3/microservice/config_7b.yaml`：7B 服务配置。
- `week3/microservice/scripts/`：base/LoRA 服务启动脚本和 quick start 说明。
- `week3/microservice/validation/`：人工验证脚本。
- `week3/microservice/logs/`：本地调用日志目录，已加入 `.gitignore`。

## 验证方式

```bash
cd ../week3/microservice
./scripts/start_3b_lora.sh
python validation/manual_chat.py
```

根据需要也可以启动 7B 或 base 对照脚本，观察同一问题在 base 与 LoRA 下的身份回答、禁限寄回答和 EMS 场景一致性。

## 交付重点

- 明确区分 base 与 LoRA，不能用 mock 结果冒充 LoRA。
- 3B/7B 配置要可切换、可复现。
- 人工验证日志要能追溯每一次完整调用，不把多轮对话拆成多份难读日志。
