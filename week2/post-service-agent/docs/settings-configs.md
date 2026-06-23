# Settings And Configs

本文档说明本项目里每个配置文件分别负责什么，避免把 Django、AI 工具包、运行环境配置混在一起。

## 配置分层

项目配置分三层：

1. Django 配置：负责 Web、数据库连接、静态资源、已安装 app。
2. post_ai 配置：负责 AI 工具包、模型 provider、向量库 provider、数据路径。
3. 环境变量配置：负责本机运行时覆盖默认值，例如数据库账号、端口、模型服务地址。

优先级规则：

```text
环境变量 / .env > config/post_ai.yaml > 代码默认值
```

也就是说，`config/post_ai.yaml` 是有效配置文件，但同名环境变量会覆盖它。

## config/settings.py

这是 Django 自己的 settings module。

负责：

- Django `SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`
- `INSTALLED_APPS`
- Django template 路径
- Django ORM 数据库连接
- 静态资源路径与 `STATIC_VERSION`
- `POST_AI_CONFIG_PATH`
- `POST_SERVICE_FAKE_LLM`

不负责：

- AI 模型选择
- FAISS / pgvector 向量库选择
- Ollama / vLLM / OpenRouter / FastAPI provider 细节

Django 数据库现在默认走 PostgreSQL：

```python
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
```

SQLite 只应该作为显式测试覆盖，不作为正常应用路径。

## config/post_ai.yaml

这是独立 AI 工具包 `post_ai` 的配置文件。

负责：

- `mode`
- 数据目录
- artifact 目录
- chat model provider 和 model
- embedding provider 和 model
- SFT provider 和 model
- provider 连接地址
- vector store provider
- FAISS artifact 文件位置
- pgvector 表名和 DSN

不负责：

- Django Web 配置
- Django template/static 配置
- Django ORM 数据库配置
- Docker 容器配置

当前文件是有效的。`post_ai/config.py` 会读取它，Django API 也会通过 `post_ai.pipeline` 使用这些配置。

### mode

`mode` 是大的运行模式标识。

可选值：

- `local`：本地调试模式。允许使用本地 Ollama、本地 FAISS artifact，也可以连接本地 PostgreSQL。
- `microservice`：微服务模式。Django 作为 Web/API 壳，AI/SFT 能力通过 provider 调用外部服务，向量库默认使用 PostgreSQL + pgvector。

`mode` 是总闸。

```yaml
mode: microservice

modes:
  local:
    database: local-artifacts
    vector_store:
      provider: faiss
    chat:
      provider: ollama
      model: gpt-oss:20b
    embedding:
      provider: ollama
      model: qwen3-embedding:8b
  microservice:
    database: postgresql
    vector_store:
      provider: pgvector
    chat:
      provider: ollama
      model: gpt-oss:20b
    embedding:
      provider: ollama
      model: qwen3-embedding:8b
```

当前规则：

- `mode: local` 默认使用 `modes.local.vector_store.provider`，也就是 FAISS。
- `mode: microservice` 默认使用 `modes.microservice.vector_store.provider`，也就是 pgvector。

只有显式设置环境变量 `POST_AI_VECTOR_PROVIDER` 时，才会临时覆盖 mode 对应的默认向量库。

### models

`models.chat` 控制普通聊天模型。

```yaml
models:
  chat:
    provider: ollama
    model: gpt-oss:20b
```

当前表示使用 Ollama 的 `gpt-oss:20b`。

`models.embedding` 控制 embedding 模型。

```yaml
models:
  embedding:
    provider: ollama
    model: qwen3-embedding:8b
```

当前表示使用 Ollama 的 `qwen3-embedding:8b`。

`models.sft` 控制 SFT 模型。

```yaml
models:
  sft:
    provider:
    model:
```

当前为空，表示不存在可切换的 SFT 模型。前端勾选 SFT 时应显示错误提示，不应假装切换成功。

### providers

所有模型调用必须通过 provider adapter。

当前 provider：

- `ollama`：本地 Ollama。
- `vllm`：vLLM 占位。
- `openrouter`：OpenRouter 占位。
- `fastapi`：用户自建 SFT/模型微服务占位。

业务代码不应该直接调用 Ollama、vLLM、OpenRouter 或 FastAPI URL，而应该通过 provider registry。

### vector_store

这是 RAG 向量库的 provider 配置。默认由 `mode` 选择。

可选值：

- `pgvector`：正式 PostgreSQL + pgvector 路径。
- `faiss`：本地 fallback / 调试路径。

当前默认：

```yaml
mode: microservice

modes:
  microservice:
    database: postgresql
    vector_store:
      provider: pgvector
```

如果要长期切换，请改 `mode`。

如果只想临时覆盖：

```bash
export POST_AI_VECTOR_PROVIDER=faiss
```

## post_ai/config.py

这是 `post_ai` 配置加载器，不是配置文件。

负责：

- 读取 `config/post_ai.yaml`
- 读取 `.env`
- 合并环境变量覆盖
- 生成 `AppConfig`
- 生成 `ProviderSettings`
- 生成 `VectorStoreSettings`
- 当 `POST_AI_PGVECTOR_DSN` 为空时，从 `DJANGO_DB_*` 拼出 pgvector DSN

关键点：

- 默认会加载 `config/post_ai.yaml`
- 设置 `POST_AI_IGNORE_YAML=1` 后，才会跳过 YAML，完全走环境变量
- 环境变量优先级高于 YAML

## .env

这是本机真实运行配置文件。

负责：

- 本机 Django 数据库连接
- 本机 Django debug/host
- 本机模型 provider 覆盖
- 本机 vector provider 覆盖
- 本机端口和服务地址

`.env` 不应提交到 git。

## .env.example

这是给开发者参考的环境变量模板。

负责：

- 说明需要哪些环境变量
- 给出本地开发默认值
- 说明哪些 provider 是可选占位

`.env.example` 应该提交到 git。

如果新增环境变量，需要同步更新 `.env.example`。

## docker-compose.yml

负责本地 PostgreSQL + pgvector 容器。

当前只用于数据库服务，不负责 Django 和 Ollama。

数据库配置应与 `.env` 中的 `DJANGO_DB_*` 保持一致。

## start_services.sh

负责一键启动本地开发需要的三个 tmux task：

- `post-ai-postgres`
- `post-ai-ollama`
- `post-ai-django`

它不迁移数据库，不导入 RAG 数据。

首次启动或数据库为空时，需要单独执行：

```bash
python manage.py migrate
python manage.py ingest_postal_rag
```

## requirements.txt / pyproject.toml

负责 Python 依赖声明。

两个文件都要同步维护，避免不同安装方式拿到不同依赖。

当前关键依赖包括：

- Django / django-ninja
- PostgreSQL driver
- pgvector 查询需要的 psycopg/psycopg2 支持
- FAISS
- PyYAML
- Pydantic

## 配置修改原则

- Web 和数据库设置放 `config/settings.py` / `.env`。
- AI 工具包设置放 `config/post_ai.yaml`。
- 真实本机私密值放 `.env`。
- 示例和默认值放 `.env.example`。
- 依赖变化同时更新 `requirements.txt` 和 `pyproject.toml`。
- 不要把 Django settings 混进 `post_ai.yaml`。
- 不要把模型 provider 细节写死在业务代码里。
