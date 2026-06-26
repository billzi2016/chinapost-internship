#!/usr/bin/env sh

# 一键执行当前配置下的完整抓取。
# 该脚本会清空项目 data/ 目录后重新抓取，适合作为最终正式运行入口。

set -e

python3 main.py --full-run
