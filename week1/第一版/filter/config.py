"""读取同目录下的 .env 配置文件。

这里不用额外的 dotenv 依赖，保持实现足够轻：
只要是 KEY=VALUE 形式的行，就会注入到 os.environ。
"""

import os
from pathlib import Path


def load_env_file(env_path):
    """把 .env 里的键值对加载到当前进程环境变量。"""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]

        # 允许在 .env 里写 "\\n"，运行时再还原成真正换行。
        value = value.replace("\\n", "\n")
        os.environ.setdefault(key, value)


ENV_PATH = Path(__file__).resolve().parent / ".env"
# 模块导入时立即加载，保证其他脚本读取环境变量前就已经生效。
load_env_file(ENV_PATH)
