# MLX OpenAI-Compatible Microservice

这个目录提供一个基于 `FastAPI` 的本地推理服务，接口风格尽量兼容 OpenAI API。

当前实现特点：

- 推理后端使用 `mlx_lm.generate`
- 支持加载基座模型和 LoRA adapter
- 默认配置从 `config_3b.yaml` 读取，也可以切换到 `config_7b.yaml`
- 支持 `stream=true` 的 OpenAI 风格 SSE 返回
- 当前提供：
  - `GET /health`
  - `GET /v1/models`
  - `POST /v1/chat/completions`

## 目录

```text
week3/microservice/
├── app.py
├── config_3b_base.yaml
├── config_3b.yaml
├── config_7b_base.yaml
├── config_7b.yaml
├── requirements.txt
├── scripts/
│   ├── QUICK_START.md
│   ├── start_3b_base.sh
│   ├── start_3b_lora.sh
│   ├── start_7b_base.sh
│   └── start_7b_lora.sh
├── src/
│   ├── __init__.py
│   ├── adapters.py
│   ├── api.py
│   ├── api_types.py
│   ├── app_factory.py
│   ├── config.py
│   ├── generation.py
│   ├── prompts.py
│   ├── request_logger.py
│   └── schemas.py
├── test/
│   └── test_app.py
├── validation/
│   └── manual_chat.py
└── README.md
```

## 默认端口

服务默认监听：

```text
127.0.0.1:18731
```

这里特意用了一个相对不常用的端口 `18731`。

## 配置文件

3B LoRA 配置文件：

```text
week3/microservice/config_3b.yaml
```

7B LoRA 配置文件：

```text
week3/microservice/config_7b.yaml
```

Base 对照配置文件：

```text
week3/microservice/config_3b_base.yaml
week3/microservice/config_7b_base.yaml
```

主要配置项：

- `server.host`
- `server.port`
- `model.model_id`
- `model.model_path`
- `model.use_lora`
- `model.runs_root`
- `model.run_id`
- `model.rank`
- `model.adapter_path`
- `model.system_prompt`
- `generation.max_tokens`
- `generation.temperature`
- `generation.top_p`

说明：

- `config_3b.yaml` 当前指向 3B 最优配置：`qwen2.5-3b-lora-r1`
- `config_7b.yaml` 当前指向 7B 最优配置：`qwen2.5-7b-lora-r2`
- `config_3b_base.yaml` 和 `config_7b_base.yaml` 使用原始基座模型，不加载 LoRA
- `model.use_lora: false` 时服务不会解析 adapter，也不会向 `mlx_lm.generate` 传 `--adapter-path`
- `model.adapter_path` 会显式指定当前服务加载的 LoRA adapter
- 如果删除 `model.adapter_path`，服务会按 `model.runs_root/model.run_id` 和 `model.rank` 从 `best_adapter_*.json` 中解析 adapter
- 如果连 `model.rank` 也不填，服务会从该 run 下所有 rank 的 `best_adapter_*.json` 中按 `best_score` 选择最高分 adapter
- 默认 `generation.max_tokens` 为 `1536`，适合流程类回答、投诉处理模板和较长解释

## 选择 3B 或 7B

默认启动 3B：

```bash
cd .
uvicorn app:app --host 127.0.0.1 --port 18731
```

启动 7B：

```bash
cd .
MICROSERVICE_MODEL_SIZE=7b uvicorn app:app --host 127.0.0.1 --port 18731
```

也可以显式指定配置文件：

```bash
cd .
MICROSERVICE_CONFIG=config_7b.yaml uvicorn app:app --host 127.0.0.1 --port 18731
```

## 安装依赖

在可用的 Python 环境里安装：

```bash
cd .
pip install -r requirements.txt
```

说明：

- 这里假设你本机已经有可用的 `mlx-lm`
- 如果 `mlx_lm.generate` 不在当前环境 PATH 里，先切到你平时跑 MLX 的那个环境再启动服务

## 启动服务

启动 3B LoRA：

```bash
cd .
./scripts/start_3b_lora.sh
```

启动 7B LoRA：

```bash
cd .
./scripts/start_7b_lora.sh
```

启动 3B Base 对照：

```bash
cd .
./scripts/start_3b_base.sh
```

启动 7B Base 对照：

```bash
cd .
./scripts/start_7b_base.sh
```

也可以直接用 `uvicorn` 启动默认 3B：

```bash
cd .
uvicorn app:app --host 127.0.0.1 --port 18731
```

也可以直接：

```bash
cd .
python app.py
```

直接 `python app.py` 时同样支持切换 7B：

```bash
MICROSERVICE_MODEL_SIZE=7b python app.py
```

## 停止服务

如果服务在当前终端前台运行：

```bash
Ctrl+C
```

## 查看端口占用

查看 `18731` 端口是谁在占用：

```bash
lsof -i tcp:18731
```

只看进程号：

```bash
lsof -ti tcp:18731
```

## 一条命令杀掉服务

温和停止：

```bash
kill $(lsof -ti tcp:18731)
```

强制停止：

```bash
kill -9 $(lsof -ti tcp:18731)
```

如果端口没有进程，上面命令可能会报空参数；更稳一点可以用：

```bash
lsof -ti tcp:18731 | xargs kill -9
```

## 接口示例

健康检查：

```bash
curl http://127.0.0.1:18731/health
```

模型列表：

```bash
curl http://127.0.0.1:18731/v1/models
```

聊天请求：

```bash
curl http://127.0.0.1:18731/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-3b-lora-r1",
    "messages": [
      {"role": "user", "content": "我的EMS物流一直没更新，应该怎么处理？"}
    ],
    "temperature": 0.7,
    "max_completion_tokens": 256
  }'
```

Streaming 请求：

```bash
curl http://127.0.0.1:18731/v1/chat/completions \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "model": "qwen2.5-3b-lora-r1",
    "messages": [
      {"role": "user", "content": "帮我写一段邮政客服回复，说明快递延误需要先核实。"}
    ],
    "stream": true,
    "max_completion_tokens": 256
  }'
```

说明：

- 当前 `stream=true` 是兼容式流输出
- 服务会先拿到完整生成结果，再按小块用 SSE 返回
- 对客户端协议兼容，但不是底层 token 级实时生成

## 人工多轮验证

先启动服务，例如默认 3B：

```bash
cd .
uvicorn app:app --host 127.0.0.1 --port 18731
```

另开一个终端启动流式多轮对话客户端：

```bash
cd .
python validation/manual_chat.py
```

客户端启动后会先打印当前服务加载的 `config_path` 和 `adapter_path`，用于确认是否挂到了预期的 3B/7B LoRA。

验证 7B 时先用 7B 配置启动服务：

```bash
cd .
MICROSERVICE_MODEL_SIZE=7b uvicorn app:app --host 127.0.0.1 --port 18731
```

客户端命令不变：

```bash
python validation/manual_chat.py
```

常用参数：

```bash
python validation/manual_chat.py --temperature 0.2 --max-tokens 768
```

交互命令：

- `/reset`：清空多轮上下文
- `/exit` 或 `/quit`：退出

## 调用日志

服务会把每次完整调用写入一个单独的 JSON 文件：

```text
week3/microservice/logs/chat_requests/
```

文件名按日期时间、毫秒和模型名生成，例如：

```text
20260703_173012_123_qwen2.5-3b-lora-r1.json
```

文件名格式为 `YYYYMMDD_HHMMSS_mmm_model.json`。每个文件记录这一次完整调用，并使用 `indent=2` 格式化。多轮对话不会拆成多个日志文件，当前请求里的完整 `messages` 会和完整回答一起写入同一个文件。`stream=true` 和普通请求都会在完整回答生成后写日志。

## 当前限制

- 目前只实现了 `chat.completions`
- token 计数是近似值，不是 tokenizer 精确统计
- 推理速度和稳定性取决于你当前 MLX 环境、模型路径和 adapter 路径是否可用
- 当前 streaming 不是底层 token-by-token 实时生成，而是完整结果分块输出

## 测试

测试文件放在：

```text
week3/microservice/test/test_app.py
```

这套测试会：

- 先自动解析默认 `config_3b.yaml`
- 再确认当前配置里的 LoRA adapter 可以解析
- 最后做真实的接口调用和真实的 MLX 推理

注意：

- 它不是 mock 测试
- 会真实调用 `mlx_lm.generate`
- 跑起来会比普通单元测试慢

执行方式：

```bash
cd .
pytest -q test/test_app.py
```

如果只想先跑健康检查和模型列表，也可以单独指定测试：

```bash
cd .
pytest -q test/test_app.py -k "health or models"
```
