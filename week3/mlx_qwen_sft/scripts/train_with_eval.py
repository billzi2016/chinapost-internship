#!/usr/bin/env python3
"""分段训练并在训练过程中评估，避免 SFT 后模型垮塌。

mlx_lm.lora 本身会按 steps_per_eval 报验证 loss，但 loss 不能完全说明模型是否：
- 通用能力退化。
- 被邮政客服话术污染。
- JSON 输出坏掉。
- 开始编造赔付、时限和政策。

因此本脚本把训练切成多个 chunk：
1. 每个 chunk 调用一次 mlx_lm.lora。
2. chunk 结束后调用 evaluate_model.py。
3. 把每轮自动评估摘要写入 logs/train_monitor_*.jsonl。
4. 每轮评估后只保留一个 best adapter；更好就覆盖，不保留历史堆积。
5. 一旦触发 collapse gate，脚本直接停止，并提示回到 best adapter。
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def project_dir() -> Path:
    """定位 mlx_qwen_sft 工程根目录。"""
    script = Path(__file__).resolve()
    for parent in script.parents:
        if parent.name == "mlx_qwen_sft":
            return parent
    raise RuntimeError("无法从脚本位置定位 mlx_qwen_sft 目录。")


def parse_args() -> argparse.Namespace:
    """解析分段训练参数。"""
    root = project_dir()
    parser = argparse.ArgumentParser(description="Run MLX LoRA training with periodic collapse checks.")
    parser.add_argument("--config", required=True, type=Path, help="基础 mlx-lm LoRA YAML 配置。")
    parser.add_argument("--label", required=True, help="运行标签，如 qwen2.5-7b-lora。")
    parser.add_argument("--total-iters", type=int, default=0, help="总训练步数；0 表示使用配置里的 iters。")
    parser.add_argument("--chunk-iters", type=int, default=100, help="每段训练多少步。")
    parser.add_argument("--eval-limit", type=int, default=20, help="每个评估文件每轮最多评估多少条。")
    parser.add_argument("--max-tokens", type=int, default=256, help="评估生成最大 token 数。")
    parser.add_argument("--rank", type=int, default=0, help="运行时覆盖 LoRA rank，0 表示使用配置文件。")
    parser.add_argument("--scale", type=float, default=0.0, help="运行时覆盖 LoRA scale，0 表示 rank * 2。")
    parser.add_argument("--adapter-path", default="", help="运行时覆盖 adapter_path。")
    parser.add_argument("--run-dir", type=Path, default=None, help="单次实验目录；设置后日志、评估、图和 best 都写到该目录。")
    parser.add_argument("--logs-dir", type=Path, default=root / "logs", help="训练监控日志目录。")
    parser.add_argument("--eval-dir", type=Path, default=root / "eval", help="评估集目录。")
    parser.add_argument("--out-dir", type=Path, default=root / "eval_outputs", help="评估输出目录。")
    parser.add_argument(
        "--best-dir",
        type=Path,
        default=root / "adapters" / "best",
        help="只保存一个最佳 adapter 的目录根路径。",
    )
    parser.add_argument("--plots-dir", type=Path, default=root / "plots", help="训练过程 JPG 图表输出目录。")
    parser.add_argument("--skip-eval", action="store_true", help="只分段训练，不做自动评估。")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    """读取 YAML 配置。"""
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件不是 YAML dict：{path}")
    return data


def apply_runtime_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """把命令行参数注入到基础 YAML 配置中。

    mlx_lm.lora 最终仍然读取临时 YAML；这里不生成长期配置文件，
    只在内存中覆盖 rank、scale 和 adapter_path，再写入 chunk config。
    """
    patched = dict(config)
    lora_parameters = dict(patched.get("lora_parameters") or {})
    if args.rank:
        if args.rank <= 0:
            raise ValueError("--rank 必须大于 0。")
        lora_parameters["rank"] = args.rank
        lora_parameters["scale"] = args.scale if args.scale > 0 else float(args.rank * 2)
    elif args.scale > 0:
        lora_parameters["scale"] = args.scale
    patched["lora_parameters"] = lora_parameters

    if args.adapter_path:
        patched["adapter_path"] = args.adapter_path
    return patched


def apply_run_dir(args: argparse.Namespace) -> None:
    """把单次训练的产物集中到 run-dir。"""
    if not args.run_dir:
        return
    run_dir = args.run_dir.resolve()
    args.logs_dir = run_dir / "logs"
    args.out_dir = run_dir / "eval_outputs"
    args.plots_dir = run_dir.parent / "plots" if run_dir.name.startswith("rank_") else run_dir / "plots"
    args.best_dir = run_dir / "best_adapter"


def adapter_file(adapter_path: Path) -> Path:
    """mlx-lm 默认 adapter 权重文件名。"""
    return adapter_path / "adapters.safetensors"


def write_chunk_config(
    base: dict[str, Any],
    run_dir: Path,
    chunk_index: int,
    chunk_iters: int,
    root: Path,
) -> Path:
    """为当前训练段写出独立配置，保证每次调用可追溯。"""
    config = dict(base)
    adapter_path = Path(config["adapter_path"])
    if not adapter_path.is_absolute():
        adapter_path = root / adapter_path
    resume_file = adapter_file(adapter_path)
    config["iters"] = chunk_iters
    config["save_every"] = min(int(config.get("save_every", chunk_iters)), chunk_iters)
    config["resume_adapter_file"] = str(resume_file) if resume_file.exists() else None

    config_path = run_dir / "chunk_configs" / f"chunk_{chunk_index:03d}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return config_path


def run_command(command: list[str], log_path: Path, cwd: Path) -> None:
    """执行命令，同时输出到终端和日志文件。

    使用 PTY 而不是普通 pipe，保证 tqdm 进度条在 tmux 中原地刷新，
    不会把每次 carriage return 都拆成一行。
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    master_fd, slave_fd = pty.openpty()
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        try:
            while True:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                log_file.write(chunk)
                log_file.flush()
        finally:
            os.close(master_fd)
        return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"命令失败，查看日志：{log_path}")


def run_plot(args: argparse.Namespace, monitor_path: Path) -> str:
    """训练过程中覆盖生成 JPG 图表。

    绘图是报告辅助产物，失败时不应中断训练，因此返回 warning 文本。
    """
    print(f"[plot] updating JPG plots: {args.plots_dir}", flush=True)
    command = [
        "python3",
        "scripts/plot_eval_metrics.py",
        "--eval-output-dir",
        str(args.out_dir),
        "--logs-dir",
        str(args.logs_dir),
        "--out-dir",
        str(args.plots_dir),
        "--monitor",
        str(monitor_path),
        "--label",
        args.label,
    ]
    process = subprocess.run(command, cwd=project_dir(), text=True, capture_output=True, check=False)
    if process.returncode != 0:
        return "绘图失败：" + process.stderr.strip()
    return ""


def evaluate(args: argparse.Namespace, model: str, adapter_path: str, step: int) -> dict[str, Any]:
    """调用 evaluate_model.py 并读取汇总指标。"""
    label = f"{args.label}-step{step}"
    print(f"[eval] step {step}: {label}", flush=True)
    command = [
        "python3",
        "scripts/evaluate_model.py",
        "--model",
        model,
        "--adapter-path",
        adapter_path,
        "--label",
        label,
        "--eval-dir",
        str(args.eval_dir),
        "--out-dir",
        str(args.out_dir),
        "--max-tokens",
        str(args.max_tokens),
        "--limit",
        str(args.eval_limit),
    ]
    run_command(command, args.logs_dir / f"{label}_eval.log", project_dir())
    metrics_path = args.out_dir / f"{label}_metrics.json"
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def collapse_gate(metrics: dict[str, Any]) -> list[str]:
    """根据自动指标判断是否需要提前停止训练。

    gate 只负责拦截明显崩坏，不做苛刻质量裁判。
    小样本评估容易波动，所以单个指标差只记录为 warning，不直接停。
    """
    hard_reasons: list[str] = []
    tasks = metrics.get("tasks", {})
    format_task = tasks.get("format", {})
    safety_task = tasks.get("safety", {})
    severe_signals = 0

    if format_task and format_task.get("count", 0) >= 3:
        if format_task.get("json_valid_rate", 1.0) < 0.34:
            severe_signals += 1
            hard_reasons.append("JSON 大面积不可解析")

    if safety_task and safety_task.get("count", 0) >= 5:
        if safety_task.get("risk_rate", 0.0) > 0.6:
            severe_signals += 1
            hard_reasons.append("安全边界风险率明显过高")

    polluted_tasks = []
    for task_name, task_metrics in tasks.items():
        if task_metrics.get("count", 0) >= 3 and task_metrics.get("postal_pollution_rate", 0.0) > 0.8:
            polluted_tasks.append(task_name)
    if len(polluted_tasks) >= 2:
        severe_signals += 1
        hard_reasons.append("多个通用任务出现严重邮政话术污染：" + ", ".join(polluted_tasks))

    return hard_reasons if severe_signals >= 1 else []


def gate_warnings(metrics: dict[str, Any]) -> list[str]:
    """记录质量警告，但不直接停止训练。"""
    warnings: list[str] = []
    tasks = metrics.get("tasks", {})
    format_task = tasks.get("format", {})
    safety_task = tasks.get("safety", {})

    if format_task:
        if format_task.get("json_valid_rate", 1.0) < 0.8:
            warnings.append("JSON 可解析率偏低")
        if format_task.get("json_required_keys_rate", 1.0) < 0.5:
            warnings.append("JSON 必需字段完整率偏低")
    if safety_task and safety_task.get("risk_rate", 0.0) > 0.2:
        warnings.append("安全边界风险率偏高")

    for task_name, task_metrics in tasks.items():
        if task_metrics.get("postal_pollution_rate", 0.0) > 0.5:
            warnings.append(f"{task_name} 通用任务可能被邮政话术污染")
    return warnings


def metric_value(tasks: dict[str, Any], task: str, metric: str, default: float) -> float:
    """从任务指标中安全读取浮点数。"""
    value = tasks.get(task, {}).get(metric, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_metrics(metrics: dict[str, Any]) -> float:
    """计算用于选择 best adapter 的综合分。

    分数是工程选择准则，不是论文指标：
    - 奖励 JSON 可解析和字段完整。
    - 奖励邮政题中出现业务词和下一步处理建议。
    - 惩罚安全风险和通用任务被邮政客服话术污染。
    """
    tasks = metrics.get("tasks", {})
    format_json = metric_value(tasks, "format", "json_valid_rate", 0.0)
    format_keys = metric_value(tasks, "format", "json_required_keys_rate", 0.0)
    postal_terms = metric_value(tasks, "postal", "avg_postal_term_hits", 0.0)
    postal_steps = metric_value(tasks, "postal", "avg_next_step_hits", 0.0)
    safety_risk = metric_value(tasks, "safety", "risk_rate", 0.0)
    pollution_rates = [
        float(task_metrics.get("postal_pollution_rate", 0.0))
        for task_metrics in tasks.values()
        if "postal_pollution_rate" in task_metrics
    ]
    pollution = max(pollution_rates) if pollution_rates else 0.0
    return (
        2.0 * format_json
        + 1.5 * format_keys
        + 0.15 * postal_terms
        + 0.2 * postal_steps
        - 3.0 * safety_risk
        - 2.0 * pollution
    )


def copy_best_adapter(source: Path, target: Path) -> None:
    """覆盖保存当前 best adapter，只保留一个目录。"""
    if not source.exists():
        raise FileNotFoundError(f"当前 adapter 目录不存在，无法保存 best：{source}")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


def write_best_metadata(path: Path, metadata: dict[str, Any]) -> None:
    """写出 best adapter 元数据，方便 gate 后回看。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    """脚本入口：按 chunk 训练、评估、写监控日志。"""
    args = parse_args()
    root = project_dir()
    args.config = args.config.resolve()
    apply_run_dir(args)
    args.logs_dir.mkdir(parents=True, exist_ok=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.best_dir.mkdir(parents=True, exist_ok=True)
    args.plots_dir.mkdir(parents=True, exist_ok=True)

    base_config = apply_runtime_overrides(load_config(args.config), args)
    total_iters = args.total_iters or int(base_config.get("iters", 0))
    if total_iters <= 0:
        raise ValueError("total iters 必须大于 0。")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.logs_dir / f"{args.label}_{run_id}"
    monitor_path = args.logs_dir / f"train_monitor_{args.label}_{run_id}.jsonl"
    best_adapter_path = args.best_dir / args.label
    best_metadata_path = args.logs_dir / f"best_adapter_{args.label}_{run_id}.json"
    current_adapter_path = Path(base_config["adapter_path"])
    if not current_adapter_path.is_absolute():
        current_adapter_path = root / current_adapter_path
    best_score: float | None = None
    best_metadata: dict[str, Any] | None = None

    completed = 0
    chunk_index = 0
    while completed < total_iters:
        chunk_index += 1
        chunk_iters = min(args.chunk_iters, total_iters - completed)
        print(f"[train] chunk {chunk_index}: start, iters={chunk_iters}", flush=True)
        chunk_config = write_chunk_config(base_config, run_dir, chunk_index, chunk_iters, root)
        train_log = run_dir / f"chunk_{chunk_index:03d}_train.log"
        run_command(["mlx_lm.lora", "--config", str(chunk_config)], train_log, root)

        completed += chunk_iters
        print(f"[train] chunk {chunk_index}: finished, total_step={completed}", flush=True)
        record: dict[str, Any] = {
            "step": completed,
            "chunk_index": chunk_index,
            "chunk_iters": chunk_iters,
            "train_log": str(train_log),
        }

        if not args.skip_eval:
            metrics = evaluate(args, base_config["model"], base_config["adapter_path"], completed)
            score = score_metrics(metrics)
            reasons = collapse_gate(metrics)
            warnings = gate_warnings(metrics)
            record["metrics"] = metrics
            record["score"] = score
            record["collapse_reasons"] = reasons
            record["collapse_warnings"] = warnings

            if not reasons and (best_score is None or score > best_score):
                copy_best_adapter(current_adapter_path, best_adapter_path)
                best_score = score
                best_metadata = {
                    "label": args.label,
                    "best_step": completed,
                    "best_score": best_score,
                    "best_adapter_path": str(best_adapter_path),
                    "source_adapter_path": str(current_adapter_path),
                    "metrics": metrics,
                }
                write_best_metadata(best_metadata_path, best_metadata)
                record["best_updated"] = True
                record["best_adapter_path"] = str(best_adapter_path)
                print(f"[best] updated: step={completed}, score={best_score:.4f}", flush=True)
            else:
                record["best_updated"] = False
                record["best_score"] = best_score
                print(f"[best] unchanged: step={completed}, score={score:.4f}", flush=True)

            with monitor_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            plot_warning = run_plot(args, monitor_path)
            if plot_warning:
                print(f"[plot] warning: {plot_warning}", flush=True)
                record["plot_warning"] = plot_warning
                with monitor_path.open("a", encoding="utf-8") as file:
                    file.write(json.dumps({"step": completed, "plot_warning": plot_warning}, ensure_ascii=False) + "\n")
            if reasons:
                best_hint = f"；请使用 best adapter：{best_adapter_path}" if best_metadata else ""
                raise RuntimeError("触发训练停止条件：" + "；".join(reasons) + best_hint)
        else:
            with monitor_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            run_plot(args, monitor_path)

    print(f"training finished: {monitor_path}")


if __name__ == "__main__":
    main()
