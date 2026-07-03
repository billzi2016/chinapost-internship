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
from typing import Any


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
    parser.add_argument("--resume-run-dir", type=Path, default=None, help="从已有 sweep 目录继续；不传则新建时间戳目录。")
    parser.add_argument("--dry-run", action="store_true", help="只打印命令，不执行。")
    return parser.parse_args()


def build_command(args: argparse.Namespace, rank: int, rank_dir: Path, start_step: int = 0) -> list[str]:
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
    if start_step:
        command.extend(["--start-step", str(start_step)])
    if args.total_iters:
        command.extend(["--total-iters", str(args.total_iters)])
    return command


def read_run_config(run_dir: Path) -> dict[str, Any]:
    """读取已有 sweep 的总配置。"""
    config_path = run_dir / "run_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"缺少 run_config.json：{config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"run_config.json 不是 JSON object：{config_path}")
    return data


def apply_resume_config(args: argparse.Namespace, run_config: dict[str, Any]) -> None:
    """用已有 run_config 覆盖命令参数，保证续跑沿用原实验设置。"""
    args.config = str(run_config["config"])
    args.label_prefix = str(run_config["label_prefix"])
    args.adapter_prefix = str(run_config["adapter_prefix"])
    args.ranks = [int(rank) for rank in run_config["ranks"]]
    args.chunk_iters = int(run_config["chunk_iters"])
    args.eval_limit = int(run_config["eval_limit"])
    args.total_iters = int(run_config["total_iters"])
    args.max_tokens = int(run_config["max_tokens"])


def total_iters_from_config(args: argparse.Namespace, root: Path) -> int:
    """读取本次 rank 的目标训练步数。"""
    if args.total_iters:
        return args.total_iters
    import yaml

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"配置文件不是 YAML dict：{config_path}")
    return int(config.get("iters", 0))


def last_completed_step(rank_dir: Path) -> int:
    """从 rank monitor 日志读取最后完成 step。"""
    monitors = sorted((rank_dir / "logs").glob("train_monitor_*.jsonl"))
    if not monitors:
        return 0
    last_step = 0
    for line in monitors[-1].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        step = record.get("step")
        if isinstance(step, int):
            last_step = max(last_step, step)
    return last_step


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
    if args.resume_run_dir:
        run_dir = args.resume_run_dir
        if not run_dir.is_absolute():
            run_dir = root / run_dir
        if run_dir.exists():
            run_config = read_run_config(run_dir)
            apply_resume_config(args, run_config)
            run_id = str(run_config.get("run_id", run_dir.name))
            run_name = str(run_config.get("run_name", run_id))
        else:
            print(f"[rank-sweep] resume dir not found, starting a new run: {run_dir}", flush=True)
            args.resume_run_dir = None
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = args.run_name or f"{args.label_prefix}_rank_sweep"
            run_id = f"{timestamp}_{run_name}"
            run_dir = args.runs_dir / run_id
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = args.run_name or f"{args.label_prefix}_rank_sweep"
        run_id = f"{timestamp}_{run_name}"
        run_dir = args.runs_dir / run_id
    print(f"[rank-sweep] run_dir={run_dir}", flush=True)
    total_iters = total_iters_from_config(args, root)
    if not args.dry_run and not args.resume_run_dir:
        write_run_config(args, run_id, run_dir, run_name)
    for rank in args.ranks:
        rank_dir = run_dir / f"rank_{rank}"
        start_step = last_completed_step(rank_dir) if args.resume_run_dir else 0
        if start_step >= total_iters:
            print(f"[rank-sweep] skip rank {rank}: completed {start_step}/{total_iters}", flush=True)
            continue
        if start_step:
            print(f"[rank-sweep] resume rank {rank}: completed {start_step}/{total_iters}", flush=True)
        command = build_command(args, rank, rank_dir, start_step=start_step)
        print("[rank-sweep]", " ".join(command), flush=True)
        if args.dry_run:
            continue
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
