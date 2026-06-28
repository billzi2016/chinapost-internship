#!/usr/bin/env sh

# 一键执行当前配置下的完整抓取。
# 该脚本会清空项目 data/ 目录后重新抓取，适合作为最终正式运行入口。

set -e

mkdir -p data/logs

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="data/logs/full_run_${timestamp}.log"

echo "日志文件: ${log_file}"

PYTHONUNBUFFERED=1 python3 -u main.py --full-run 2>&1 | tee "${log_file}"
