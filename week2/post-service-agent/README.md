# Post Service Agent

邮政客服智能助手 Django 项目。

当前结构遵循 KISS：

- `post_ai/`：完整 AI 工具包，包含 provider、RAG、FAISS vector store、数据映射、prompt、工单 JSON schema 和 AI 自己的测试。
- `apps/core/`：Django ORM 模型，包含会话、消息、邮政文档、引用、工单。
- `apps/api/`：django-ninja API 和 SSE。
- `apps/web/`：Django templates 页面和静态资源入口。

Django 只调用 `post_ai`，不拆散 `post_ai`，也不在 view/API 层直接写模型或检索细节。

## 技术栈

- Python 3.13，当前使用 Anaconda base：`/opt/anaconda3/bin/python`
- Django
- django-ninja
- Django templates
- 原生 JavaScript
- Bootstrap 兼容 CSS，本地 vendor 文件
- Markdown 渲染和 sanitizer，本地 vendor 文件
- FAISS，当前阶段的本地 vector store
- PostgreSQL + pgvector，后续正式数据库/vector store
- Ollama provider，当前默认 chat/embedding provider
- vLLM / OpenRouter / FastAPI provider，占位

## 配置

AI 工具包使用自己的 YAML 配置：

```text
config/post_ai.yaml
```

这个文件只属于 `post_ai`。Django 后续使用自己的 `settings.py` 和环境配置，不把 Django 的 Web、数据库、静态资源配置混进 `post_ai.yaml`。

配置项包括：

- chat provider
- embedding provider
- SFT provider
- vector store provider
- FAISS artifact 路径
- pgvector 占位配置

## 当前范围

- Provider 标准接口
- Ollama provider
- vLLM / OpenRouter / FastAPI provider 占位
- Qwen3 embedding query 前缀
- CSDS 数据读取
- `llm_filter` 到 CSDS 映射
- FAISS 向量检索
- RAG prompt
- 工单 JSON schema
- `post_ai/tests/unit` 单元测试
- `post_ai/tests/integration` 整体测试
- Django KISS app 骨架
- Django 页面/API/SSE 接线
- Django 测试

## FAISS Artifact

当前阶段用 FAISS 跑通 RAG，正式 artifact 位于：

```text
artifacts/faiss/postal.faiss
artifacts/faiss/postal_metadata.json
```

构建命令：

```bash
PYTHONPATH=. python -m post_ai.build_faiss
```

当前 artifact 使用已有数据：

- embedding 来源：`week2/data/embeddings/dialogue_embeddings.h5`
- metadata 来源：`week2/data/embeddings/dialogue_metadata.json`
- provider 标记：`old-h5`
- 文档数：6321

FAISS 作为 vector provider 封装在 `post_ai/vectorstores/faiss_store.py`。后续接入 Django + pgvector 时，保留 RAG 上层接口，把 `config/post_ai.yaml` 的 `vector_store.provider` 从 `faiss` 切到 `pgvector`，再实现 `post_ai/vectorstores/pgvector_store.py` 即可。

## 分离原则

- AI 工具包代码和 AI 测试都放在 `post_ai/` 内。
- Django 后续会有自己的 apps 和测试目录。
- 不把 Django 测试和 AI 工具包测试混在一起。
- `post_ai/` 后续可以整体移动进 Django 项目。

## Quickstart

以下命令默认在项目目录执行：

```bash
cd /Users/bizi/Desktop/邮政实习/week2/post-service-agent
```

### 1. 使用 Anaconda base

本机当前用 Anaconda base，不创建 venv：

```bash
/opt/anaconda3/bin/python --version
```

如果 shell 里的 `python3` 指到 Homebrew，不影响项目命令，统一使用：

```bash
/opt/anaconda3/bin/python
```

### 2. 检查依赖

```bash
/opt/anaconda3/bin/python -c "import django, ninja, faiss, yaml; print('ok')"
```

如果缺 Django 或 django-ninja，用 Anaconda base 的 pip 安装：

```bash
/opt/anaconda3/bin/pip install 'Django>=5' 'django-ninja>=1'
```

### 3. 生成 FAISS artifact

FAISS artifact 是本地构建产物，不进 Git。

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```

生成位置：

```text
artifacts/faiss/postal.faiss
artifacts/faiss/postal_metadata.json
```

### 4. 初始化 Django 数据库

当前阶段可以用默认本地 `db.sqlite3` 跑通 Web/API。该文件已被 Git 忽略。后续正式改 PostgreSQL。

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py migrate
```

### 5. 启动 Django

默认端口：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:8000
```

打开：

```text
http://127.0.0.1:8000/
```

如果 `8000` 被占用，换端口，例如：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:8010
```

### 6. 查找并 kill 占用端口的进程

查看端口占用：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

输出里找到 `PID` 后终止：

```bash
kill <PID>
```

如果普通 kill 不退出，再用：

```bash
kill -9 <PID>
```

常见替换端口：

```text
8000 -> 8010 -> 8020
```

## Docker

构建镜像：

```bash
docker build -t post-service-agent .
```

运行：

```bash
docker run --rm -p 8000:8000 post-service-agent
```

如果宿主机 `8000` 端口冲突，换宿主机端口：

```bash
docker run --rm -p 8010:8000 post-service-agent
```

当前 `.dockerignore` 会排除：

- FAISS artifact
- 数据目录
- Python cache
- SQLite 本地文件
- `.env`

容器内如果要用 FAISS artifact 和数据目录，后续应通过 volume 挂载，不把大文件打进镜像。

## 运行测试

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m pytest -p no:cacheprovider post_ai/tests/unit post_ai/tests/integration
PYTHONPATH=. /opt/anaconda3/bin/python manage.py test tests.django
```
