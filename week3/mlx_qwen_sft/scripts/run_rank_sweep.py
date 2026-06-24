#!/usr/bin/env python3
"""循环运行 LoRA rank sweep，不生成长期 YAML。

每个 rank 都通过 train_with_eval.py 的 parser 注入：
- --rank
- --scale
- --adapter-path

这样只维护一份基础 YAML，同时每个 rank 都有独立 label、adapter、
eval_outputs 和 plots，方便后续画 rank 曲线。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


DEFAULT_RANKS = [1, 2, 4, 8, 16, 32]


def project_dir() -> Path:
    """定位 mlx_qwen_sft 工程根目录。"""
    script = Path(__file__).resolve()
    for parent in script.parents:
        if parent.name == "mlx_qwen_sft":
            return parent
    raise RuntimeError("无法从脚本位置定位 mlx_qwen_sft 目录。")


def parse_args() -> argparse.Namespace:
    """解析 rank sweep 参数。"""
    parser = argparse.ArgumentParser(description="Run LoRA rank sweep through train_with_eval.py.")
    parser.add_argument("--config", required=True, help="基础 LoRA YAML 配置。")
    parser.add_argument("--label-prefix", required=True, help="label 前缀，例如 qwen2.5-3b-lora。")
    parser.add_argument("--adapter-prefix", required=True, help="adapter 前缀，例如 ./adapters/qwen2.5-3b。")
    parser.add_argument("--ranks", type=int, nargs="+", default=DEFAULT_RANKS, help="要扫描的 rank 列表。")
    parser.add_argument("--chunk-iters", type=int, default=100, help="每段训练步数。")
    parser.add_argument("--eval-limit", type=int, default=20, help="每个评估文件每轮最多评估多少条。")
    parser.add_argument("--total-iters", type=int, default=0, help="总训练步数，0 表示使用配置文件。")
    parser.add_argument("--max-tokens", type=int, default=256, help="评估生成最大 token 数。")
    parser.add_argument("--runs-dir", type=Path, default=project_dir() / "runs", help="实验归档目录。")
    parser.add_argument("--run-name", default="", help="本次 sweep 的语义名称；最终目录会自动加时间戳。")
    parser.add_argument("--dry-run", action="store_true", help="只打印命令，不执行。")
    return parser.parse_args()


def build_command(args: argparse.Namespace, rank: int, rank_dir: Path) -> list[str]:
    """构造单个 rank 的训练命令。"""
    scale = float(rank * 2)
    label = f"{args.label_prefix}-r{rank}"
    adapter_path = f"{args.adapter_prefix}-r{rank}"
    command = [
        "python3",
        "scripts/train_with_eval.py",
        "--config",
        args.config,
        "--label",
        label,
        "--rank",
        str(rank),
        "--scale",
        str(scale),
        "--adapter-path",
        adapter_path,
        "--run-dir",
        str(rank_dir),
        "--chunk-iters",
        str(args.chunk_iters),
        "--eval-limit",
        str(args.eval_limit),
        "--max-tokens",
        str(args.max_tokens),
    ]
    if args.total_iters:
        command.extend(["--total-iters", str(args.total_iters)])
    return command


def write_run_config(args: argparse.Namespace, run_id: str, run_dir: Path, run_name: str) -> None:
    """保存本次 sweep 的总配置。"""
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "run_name": run_name,
        "config": args.config,
        "label_prefix": args.label_prefix,
        "adapter_prefix": args.adapter_prefix,
        "ranks": args.ranks,
        "chunk_iters": args.chunk_iters,
        "eval_limit": args.eval_limit,
        "total_iters": args.total_iters,
        "max_tokens": args.max_tokens,
    }
    (run_dir / "run_config.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    """脚本入口：按 rank 顺序运行训练。"""
    root = project_dir()
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = args.run_name or f"{args.label_prefix}_rank_sweep"
    run_id = f"{timestamp}_{run_name}"
    run_dir = args.runs_dir / run_id
    print(f"[rank-sweep] run_dir={run_dir}", flush=True)
    if not args.dry_run:
        write_run_config(args, run_id, run_dir, run_name)
    for rank in args.ranks:
        rank_dir = run_dir / f"rank_{rank}"
        command = build_command(args, rank, rank_dir)
        print("[rank-sweep]", " ".join(command), flush=True)
        if args.dry_run:
            continue
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
