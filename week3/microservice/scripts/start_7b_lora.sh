#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export MICROSERVICE_MODEL_SIZE=7b
exec uvicorn app:app --host 127.0.0.1 --port 18731
