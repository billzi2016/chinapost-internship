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
/opt/anaconda3/bin/python -c "import django, ninja, faiss, yaml, psycopg; print('ok')"
```

如果缺 Django 或 django-ninja，用 Anaconda base 的 pip 安装：

```bash
/opt/anaconda3/bin/pip install -r requirements.txt
```

## 3. 运行模式

项目使用 `POST_SERVICE_MODE` 表示大的运行模式：

- `local`：本地调试模式，可以切 FAISS，也可以用假 LLM 调 UI。
- `microservice`：正式服务模式，Django 使用 PostgreSQL，RAG 使用 pgvector，模型通过 provider 调用。

配置位置：

```text
.env
.env.example
config/post_ai.yaml
```

复制示例配置：

```bash
cp .env.example .env
```

切到 local：

```bash
export POST_SERVICE_MODE=local
export POST_AI_VECTOR_PROVIDER=faiss
```

切到 microservice：

```bash
export POST_SERVICE_MODE=microservice
export POST_AI_VECTOR_PROVIDER=pgvector
```

## 4. Local：生成 FAISS Artifact

FAISS artifact 是本地构建产物，不进 Git。

```bash
PYTHONPATH=. /opt/anaconda3/bin/python -m post_ai.build_faiss
```

生成位置：

```text
artifacts/faiss/postal.faiss
artifacts/faiss/postal_metadata.json
```

FAISS 保留为 local 调试 provider，不是正式默认路径。

## 5. Local：SQLite 临时调试

如果只想临时调 UI，可以显式切 SQLite。正式开发不要用这个路径。

```bash
export DJANGO_DB_ENGINE=django.db.backends.sqlite3
export DJANGO_DB_NAME=/Users/bizi/Desktop/邮政实习/week2/post-service-agent/db.sqlite3
export POST_SERVICE_FAKE_LLM=1
export POST_AI_VECTOR_PROVIDER=faiss
```

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py migrate
```

## 6. Microservice：启动 PostgreSQL + pgvector

正式数据库使用 PostgreSQL。`pgvector` 是 PostgreSQL 扩展，不是单独数据库。

### 6.1 Docker Compose 推荐

启动数据库微服务：

```bash
docker compose up -d postgres
```

查看状态：

```bash
docker compose ps
docker logs -f post-service-postgres
```

停止：

```bash
docker compose stop postgres
```

删除容器但保留 volume：

```bash
docker compose rm postgres
```

删除数据库 volume 重新开始：

```bash
docker compose down -v
```

### 6.2 Homebrew PostgreSQL

查看本机是否有 PostgreSQL：

```bash
which psql
psql --version
```

安装 pgvector：

```bash
brew install pgvector
```

注意：Homebrew 的 `pgvector` 必须和正在运行的 PostgreSQL 大版本匹配。比如本机如果运行 `postgresql@16`，但 `pgvector` 安装到了 `share/postgresql@17/extension`，执行 `CREATE EXTENSION vector` 会报：

```text
extension "vector" is not available
Could not open extension control file ".../postgresql@16/.../vector.control"
```

这时不要硬迁移。选择其中一种：

- 启动 Docker 的 `pgvector/pgvector:pg16` 镜像。
- 或安装/切换到 Homebrew PostgreSQL 17，让 PostgreSQL 和 pgvector 扩展目录同版本。

启动 PostgreSQL 服务：

```bash
brew services start postgresql@16
```

如果使用 PostgreSQL 17：

```bash
brew services start postgresql@17
```

如果你安装的是其他版本，先查：

```bash
brew services list | grep postgres
```

常见服务名可能是：

```text
postgresql
postgresql@14
postgresql@15
postgresql@16
postgresql@17
```

停止 PostgreSQL：

```bash
brew services stop postgresql@16
```

如果当前 `5432` 被 `postgresql@16` 占用，而你要改用 `postgresql@17`：

```bash
brew services stop postgresql@16
brew services start postgresql@17
```

### 6.3 Docker Run

如果不想用 Homebrew，可以用 Docker 启动 PostgreSQL + pgvector：

```bash
docker run --name post-service-postgres \
  -e POSTGRES_USER=post_service \
  -e POSTGRES_PASSWORD=post_service \
  -e POSTGRES_DB=post_service_agent \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
```

如果 `5432` 被占用，换宿主机端口，例如：

```bash
docker run --name post-service-postgres \
  -e POSTGRES_USER=post_service \
  -e POSTGRES_PASSWORD=post_service \
  -e POSTGRES_DB=post_service_agent \
  -p 15432:5432 \
  -d pgvector/pgvector:pg16
```

这时 Django 的 `DJANGO_DB_PORT` 要用 `15432`。

停止并删除容器：

```bash
docker stop post-service-postgres
docker rm post-service-postgres
```

### 6.4 查找并 Kill PostgreSQL 端口占用

查看 5432 端口占用：

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

输出里找到 `PID` 后终止：

```bash
kill <PID>
```

如果普通 kill 不退出，再用：

```bash
kill -9 <PID>
```

### 6.5 创建数据库和 pgvector 扩展

进入 psql：

```bash
psql postgres
```

创建用户和数据库：

```sql
CREATE USER post_service WITH PASSWORD 'post_service';
CREATE DATABASE post_service_agent OWNER post_service;
```

连接项目数据库：

```sql
\c post_service_agent
```

启用 pgvector：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

确认扩展可用：

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

退出：

```sql
\q
```

如果使用 `docker compose up -d postgres`，用户、密码和数据库会自动创建。Django migration 也会执行 `CREATE EXTENSION IF NOT EXISTS vector`。

当前本机实测状态：

- Docker daemon 未启动时，`docker compose up -d postgres` 会失败。
- Homebrew PostgreSQL 16 可以启动。
- Homebrew `pgvector` 安装后如果只提供 PostgreSQL 17 的扩展目录，PostgreSQL 16 仍无法 `CREATE EXTENSION vector`。
- 这种情况下需要先解决 Docker daemon 或 PostgreSQL/pgvector 大版本匹配，再执行 Django migration。

### 6.6 Django 使用 PostgreSQL

`.env` 默认已经是 PostgreSQL：

```bash
export POST_SERVICE_MODE=microservice
export DJANGO_DB_ENGINE=django.db.backends.postgresql
export DJANGO_DB_NAME=post_service_agent
export DJANGO_DB_USER=post_service
export DJANGO_DB_PASSWORD=post_service
export DJANGO_DB_HOST=127.0.0.1
export DJANGO_DB_PORT=5432
export POST_AI_VECTOR_PROVIDER=pgvector
```

如果 Docker 映射到了 `15432`：

```bash
export DJANGO_DB_PORT=15432
```

然后执行迁移：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py migrate
```

导入邮政 RAG 文档和 pgvector embedding：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag
```

小批量验证：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag --limit 20
```

只导入文档、不写 embedding：

```bash
PYTHONPATH=. /opt/anaconda3/bin/python manage.py ingest_postal_rag --skip-embeddings
```

## 7. 启动 Django

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

## 8. 查找并 Kill Django 端口占用

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

## 9. Docker

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
