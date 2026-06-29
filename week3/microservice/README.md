# MLX OpenAI-Compatible Microservice

这个目录提供一个基于 `FastAPI` 的本地推理服务，接口风格尽量兼容 OpenAI API。

当前实现特点：

- 推理后端使用 `mlx_lm.generate`
- 支持加载基座模型和 LoRA adapter
- 配置从 `config.yaml` 读取
- 支持 `stream=true` 的 OpenAI 风格 SSE 返回
- 当前提供：
  - `GET /health`
  - `GET /v1/models`
  - `POST /v1/chat/completions`

## 目录

```text
week3/microservice/
├── app.py
├── config.yaml
├── requirements.txt
├── test/
│   └── test_app.py
└── README.md
```

## 默认端口

服务默认监听：

```text
127.0.0.1:18731
```

这里特意用了一个相对不常用的端口 `18731`。

## 配置文件

配置文件路径：

```text
week3/microservice/config.yaml
```

主要配置项：

- `server.host`
- `server.port`
- `model.model_id`
- `model.model_path`
- `model.runs_root`
- `model.run_id`
- `model.system_prompt`
- `generation.max_tokens`
- `generation.temperature`
- `generation.top_p`

说明：

- 服务不会在 `config.yaml` 里写死单个 LoRA adapter 路径
- 它会读取 `model.runs_root/model.run_id` 下各个 `rank_*/logs/best_adapter_*.json`
- 然后自动按 `best_score` 选当前最优 LoRA

## 安装依赖

在可用的 Python 环境里安装：

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
pip install -r requirements.txt
```

说明：

- 这里假设你本机已经有可用的 `mlx-lm`
- 如果 `mlx_lm.generate` 不在当前环境 PATH 里，先切到你平时跑 MLX 的那个环境再启动服务

## 启动服务

在 `week3/microservice` 目录启动：

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
uvicorn app:app --host 127.0.0.1 --port 18731
```

也可以直接：

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
python app.py
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

- 先自动解析 `config.yaml`
- 再自动从指定 run 里选择 `best_score` 最高的 LoRA
- 最后做真实的接口调用和真实的 MLX 推理

注意：

- 它不是 mock 测试
- 会真实调用 `mlx_lm.generate`
- 跑起来会比普通单元测试慢

执行方式：

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
pytest -q test/test_app.py
```

如果只想先跑健康检查和模型列表，也可以单独指定测试：

```bash
cd /Users/bizi/Desktop/邮政实习/week3/microservice
pytest -q test/test_app.py -k "health or models"
```
