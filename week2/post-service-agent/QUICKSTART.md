# Quickstart

以下命令默认在项目目录执行：

```bash
cd /Users/bizi/Desktop/邮政实习/week2/post-service-agent
```

## 1. 使用 Anaconda Base

本机当前使用 Anaconda base，不创建 venv：

```bash
/opt/anaconda3/bin/python --version
```

如果 shell 里的 `python3` 指到 Homebrew，不影响项目命令，统一使用：

```bash
/opt/anaconda3/bin/python
```

## 2. 检查依赖

```bash
/opt/anaconda3/bin/python -c "import django, ninja, faiss, yaml; print('ok')"
```

如果缺 Django 或 django-ninja，用 Anaconda base 的 pip 安装：

```bash
/opt/anaconda3/bin/pip install 'Django>=5' 'django-ninja>=1'
```

## 3. 生成 FAISS Artifact

FAISS artifact 是本地构建产物，不进 Git。

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```

生成位置：

```text
artifacts/faiss/postal.faiss
artifacts/faiss/postal_metadata.json
```

当前 FAISS artifact 使用旧 `dialogue_embeddings.h5` 的文档向量。它可以验证 Django、SSE、引用展示和 vector store 接线，但最终语义检索需要接入 `qwen3-embedding:8b` 生成用户 query embedding。

## 4. 初始化 Django 数据库

当前阶段可以用默认本地 `db.sqlite3` 跑通 Web/API。该文件已被 Git 忽略。后续正式改 PostgreSQL。

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py migrate
```

## 5. 启动 Django

默认端口：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:8000
```

打开：

```text
http://127.0.0.1:8000/
```

确认服务：

```bash
curl -i http://127.0.0.1:8000/
curl -i http://127.0.0.1:8000/api/conversations
```

测试 SSE：

```bash
curl -i -X POST http://127.0.0.1:8000/api/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"包裹什么时候派送","use_rag":false,"use_sft":false}'
```

如果 `8000` 被占用，换端口，例如：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:8010
```

## 6. 查找并 Kill 占用端口的进程

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

## 7. Docker

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
