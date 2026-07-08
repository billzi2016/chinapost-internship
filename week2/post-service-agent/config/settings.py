"""Django 项目运行配置。

这个文件负责把 `.env`、Django 内置组件、数据库、模板、静态文件和项目自定义开关组合起来。
模型 provider、RAG、SFT 等 AI 细节不在这里展开，统一由 `config/post_ai.yaml` 和 `post_ai.config`
读取；这里只暴露 Django 运行时必须知道的开关。
"""

from __future__ import annotations

import os
from pathlib import Path

from post_ai.env import load_env_file


BASE_DIR = Path(__file__).resolve().parents[1]
# 先加载项目根目录 `.env`，后续 os.getenv 才能读到本地开发配置。
load_env_file(BASE_DIR / ".env")

# 开发环境提供默认值，生产部署时必须通过环境变量覆盖 SECRET_KEY。
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-post-service-agent")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
# POST_SERVICE_MODE 会影响 post_ai 默认选择 FAISS 还是 pgvector。
POST_SERVICE_MODE = os.getenv("POST_SERVICE_MODE", "local")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.web",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context_processors.static_version",
            ],
        },
    }
]

DATABASES = {
    "default": {
        # 默认走 PostgreSQL + pgvector；测试或临时本地调试可以用环境变量切到 SQLite。
        "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DJANGO_DB_NAME", "post_service_agent"),
        "USER": os.getenv("DJANGO_DB_USER", "post_service"),
        "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", "post_service"),
        "HOST": os.getenv("DJANGO_DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
    }
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# 前端静态资源 URL 上会带这个版本号，改 JS/CSS 后可用它规避浏览器缓存。
STATIC_VERSION = os.getenv("STATIC_VERSION", "20260623-32")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

POST_AI_CONFIG_PATH = BASE_DIR / "config" / "post_ai.yaml"
# 测试开关：为 1 时跳过真实 LLM 调用，但仍会保留配置校验路径。
POST_SERVICE_FAKE_LLM = os.getenv("POST_SERVICE_FAKE_LLM", "0") == "1"
