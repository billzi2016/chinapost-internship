# Microservice 启动脚本速查

这些脚本都需要在本机已有可用 `mlx_lm.generate` 和 `uvicorn` 的环境里运行。四个脚本都会启动同一个 FastAPI 服务：

```text
http://127.0.0.1:18731
```

同一时间只能有一个脚本占用这个端口。切换模型前先停止当前服务。

## 3B LoRA

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
./scripts/start_3b_lora.sh
```

会加载：

- 配置：`config_3b.yaml`
- 基座：`Qwen/Qwen2.5-3B-Instruct`
- LoRA：当前 3B rank sweep 里选出的 `rank_1`
- 模型名：`qwen2.5-3b-lora-r1`

用于验证当前推荐的 3B 微调模型效果。

## 7B LoRA

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
./scripts/start_7b_lora.sh
```

会加载：

- 配置：`config_7b.yaml`
- 基座：`Qwen/Qwen2.5-7B-Instruct`
- LoRA：当前 7B rank sweep 里选出的 `rank_2`
- 模型名：`qwen2.5-7b-lora-r2`

用于验证当前推荐的 7B 微调模型效果。

## 3B Base

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
./scripts/start_3b_base.sh
```

会加载：

- 配置：`config_3b_base.yaml`
- 基座：`Qwen/Qwen2.5-3B-Instruct`
- LoRA：不加载
- 模型名：`qwen2.5-3b-base`

用于和 3B LoRA 对比，查看微调前后的身份、邮政业务表达和安全边界差异。

## 7B Base

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
./scripts/start_7b_base.sh
```

会加载：

- 配置：`config_7b_base.yaml`
- 基座：`Qwen/Qwen2.5-7B-Instruct`
- LoRA：不加载
- 模型名：`qwen2.5-7b-base`

用于和 7B LoRA 对比，查看微调前后的身份、邮政业务表达和安全边界差异。

## 人工验证

服务启动后，另开一个终端运行：

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
python validation/manual_chat.py
```

客户端会先打印当前服务实际加载的配置和 adapter：

```text
service_config: ...
service_adapter: ...
model: ...
```

Base 模型的 `service_adapter` 应该是 `None`。LoRA 模型的 `service_adapter` 应该指向对应 rank 的 `best_adapter` 目录。

每次完整调用都会写入一个 JSON 日志：

```text
logs/chat_requests/YYYYMMDD_HHMMSS_mmm_model.json
```
