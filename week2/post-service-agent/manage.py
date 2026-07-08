#!/usr/bin/env python3
"""Django 命令行入口。

本文件用于执行 `runserver`、`migrate`、`test`、自定义管理命令等操作。
业务代码不要写在这里，保持为标准 Django bootstrap。
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """设置默认 settings 模块，并把命令行参数交给 Django 管理命令系统。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
