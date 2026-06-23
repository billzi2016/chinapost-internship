# Quickstart

一轮启动正式链路：PostgreSQL + pgvector + Django + RAG 导入。

```bash
cd /Users/bizi/Desktop/邮政实习/week2/post-service-agent
cp .env.example .env
```

## 1. 启动数据库

推荐 Docker Desktop 已启动时使用：

```bash
docker compose up -d postgres
docker compose ps
```

如果 `5432` 被占用，先查：

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

## 2. 迁移数据库

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py migrate
```

## 3. 导入 RAG 数据

先小批量验证：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag --limit 20
```

确认无误后导入全量：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
```

## 4. 启动 Django

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:9999
```

打开：

```text
http://127.0.0.1:9999/
```

如果 `9999` 被占用：

```bash
lsof -nP -iTCP:9999 -sTCP:LISTEN
PYTHONPATH=. /opt/anaconda3/bin/python manage.py runserver 127.0.0.1:10000
```

## 5. 可选：tmux 一键启动三个 task

如果已经完成迁移和 RAG 导入，可以用脚本打开三个独立 tmux session：

```bash
./start_services.sh
```

task 名称：

```text
post-ai-postgres
post-ai-ollama
post-ai-django
```

列出所有 tmux task：

```bash
tmux ls
```

查看某个 task：

```bash
tmux attach -t post-ai-postgres
tmux attach -t post-ai-ollama
tmux attach -t post-ai-django
```

如果 `9999` 被占用：

```bash
DJANGO_PORT=10000 ./start_services.sh
```

更多 local/faiss、Homebrew PostgreSQL、pgvector 版本排查和 Docker 细节见 `RUNBOOK.md`。
