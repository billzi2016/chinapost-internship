#!/usr/bin/env python3
"""整理第三周 SFT 原始数据到 MLX 微调工程目录。

这个脚本只负责一件事：把临时放在 week3/sft_training 下的数据文件，
整理到 PRD 约定的 week3/mlx_qwen_sft/data/raw 目录中。

设计原则：
- 数据整理动作必须脚本化，避免以后靠临时 mv/cp 命令复现。
- 默认移动文件，保留 --copy 选项用于只复制不改变源目录。
- 默认不覆盖目标文件，避免误删已经整理好的数据。
- 只处理明确列出的四个 JSON 文件，不递归搬运未知文件。
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


# 当前 SFT 原始数据应包含的固定文件。
# 后续如果新增 dev.json、metadata.json 等文件，应该先在这里显式登记，
# 再运行脚本，避免把目录中的无关临时文件带进训练工程。
EXPECTED_FILES = ("train.json", "val.json", "test.json", "who_am_i.json")


def find_week3_dir() -> Path:
    """从脚本所在路径向上查找 week3 目录。

    不使用用户机器上的绝对路径，保证整个项目移动位置后仍然可运行。
    当前脚本预期位于 week3/mlx_qwen_sft/scripts/ 下，因此向上查找
    名称为 week3 的父目录即可定位第三周工程根目录。
    """
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if parent.name == "week3":
            return parent
    raise RuntimeError("Cannot locate week3 directory from script path.")


def parse_args() -> argparse.Namespace:
    """解析命令行参数，并设置基于 week3 的默认相对目录。"""
    week3_dir = find_week3_dir()
    default_source = week3_dir / "sft_training"
    default_target = week3_dir / "mlx_qwen_sft" / "data" / "raw"

    parser = argparse.ArgumentParser(
        description="Move or copy week3/sft_training JSON files into mlx_qwen_sft/data/raw."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source,
        help="Source directory containing train.json, val.json, test.json, and who_am_i.json.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=default_target,
        help="Target raw data directory under the MLX SFT project.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of moving them.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing target files.",
    )
    parser.add_argument(
        "--keep-empty-source",
        action="store_true",
        help="Keep the source directory after moving files, even if it becomes empty.",
    )
    return parser.parse_args()


def require_source_files(source: Path) -> list[Path]:
    """检查源目录和必需文件是否存在。

    这里故意采用严格检查：
    - 源目录不存在直接失败。
    - 缺少任意一个约定文件直接失败。

    这样可以避免只搬走部分数据，导致后续训练时才发现数据不完整。
    """
    if not source.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source}")

    missing = [name for name in EXPECTED_FILES if not (source / name).is_file()]
    if missing:
        missing_text = ", ".join(missing)
        raise FileNotFoundError(f"Missing expected source files: {missing_text}")

    return [source / name for name in EXPECTED_FILES]


def ensure_target_available(files: list[Path], target: Path, overwrite: bool) -> None:
    """创建目标目录，并检查是否会覆盖已有文件。

    默认不覆盖，是为了保护已经整理过的数据。需要替换目标文件时，
    必须显式传入 --overwrite，让覆盖行为在命令里可见。
    """
    target.mkdir(parents=True, exist_ok=True)
    existing = [target / file_path.name for file_path in files if (target / file_path.name).exists()]
    if existing and not overwrite:
        existing_text = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            "Target files already exist. Use --overwrite if you want to replace them: "
            f"{existing_text}"
        )


def organize_files(
    files: list[Path],
    target: Path,
    *,
    copy: bool,
    overwrite: bool,
) -> None:
    """执行实际的数据移动或复制。

    默认使用 shutil.move，把临时源目录中的文件移动到 raw 目录。
    如果传入 --copy，则使用 shutil.copy2，尽量保留原文件元信息。
    """
    action = shutil.copy2 if copy else shutil.move
    for source_file in files:
        target_file = target / source_file.name
        if target_file.exists() and overwrite:
            target_file.unlink()
        action(str(source_file), str(target_file))
        verb = "copied" if copy else "moved"
        print(f"{verb}: {source_file} -> {target_file}")


def remove_empty_source(source: Path, *, copy: bool, keep_empty_source: bool) -> None:
    """移动完成后删除空源目录。

    只有在默认移动模式下才会尝试删除源目录：
    - --copy 时源目录仍然包含原文件，不删除。
    - --keep-empty-source 时按用户要求保留。
    - 如果源目录里还有其他文件，rmdir 会失败，脚本只提示并保留。
    """
    if copy or keep_empty_source or not source.exists():
        return
    try:
        source.rmdir()
    except OSError:
        print(f"source kept because it is not empty: {source}")
    else:
        print(f"removed empty source directory: {source}")


def main() -> None:
    """脚本入口：检查输入、准备目标、整理文件、清理空目录。"""
    args = parse_args()
    source = args.source.resolve()
    target = args.target.resolve()

    files = require_source_files(source)
    ensure_target_available(files, target, args.overwrite)
    organize_files(files, target, copy=args.copy, overwrite=args.overwrite)
    remove_empty_source(source, copy=args.copy, keep_empty_source=args.keep_empty_source)
    print(f"done: raw SFT data is under {target}")


if __name__ == "__main__":
    main()
