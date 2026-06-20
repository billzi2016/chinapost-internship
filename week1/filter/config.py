import os
from pathlib import Path


def load_env_file(env_path):
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

        value = value.replace("\\n", "\n")
        os.environ.setdefault(key, value)


ENV_PATH = Path(__file__).resolve().parent / ".env"
load_env_file(ENV_PATH)
