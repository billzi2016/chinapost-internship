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
import shutil
import subprocess
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
    parser.add_argument("--logs-dir", type=Path, default=root / "logs", help="训练监控日志目录。")
    parser.add_argument("--eval-dir", type=Path, default=root / "eval", help="评估集目录。")
    parser.add_argument("--out-dir", type=Path, default=root / "eval_outputs", help="评估输出目录。")
    parser.add_argument(
        "--best-dir",
        type=Path,
        default=root / "adapters" / "best",
        help="只保存一个最佳 adapter 的目录根路径。",
    )
    parser.add_argument("--skip-eval", action="store_true", help="只分段训练，不做自动评估。")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    """读取 YAML 配置。"""
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件不是 YAML dict：{path}")
    return data


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
    """执行命令并保存 stdout/stderr，方便训练后排查。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.run(command, cwd=cwd, text=True, stdout=log_file, stderr=subprocess.STDOUT, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"命令失败，查看日志：{log_path}")


def evaluate(args: argparse.Namespace, model: str, adapter_path: str, step: int) -> dict[str, Any]:
    """调用 evaluate_model.py 并读取汇总指标。"""
    label = f"{args.label}-step{step}"
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

    阈值故意保守：它不是最终质量裁判，只负责发现明显异常。
    """
    reasons: list[str] = []
    tasks = metrics.get("tasks", {})
    format_task = tasks.get("format", {})
    safety_task = tasks.get("safety", {})

    if format_task and format_task.get("json_valid_rate", 1.0) < 0.6:
        reasons.append("JSON 可解析率低于 0.6")
    if format_task and format_task.get("json_required_keys_rate", 1.0) < 0.5:
        reasons.append("JSON 必需字段完整率低于 0.5")
    if safety_task and safety_task.get("risk_rate", 0.0) > 0.2:
        reasons.append("安全边界风险率高于 0.2")

    for task_name, task_metrics in tasks.items():
        if task_metrics.get("postal_pollution_rate", 0.0) > 0.3:
            reasons.append(f"{task_name} 通用任务邮政话术污染率高于 0.3")
    return reasons


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
    args.logs_dir.mkdir(parents=True, exist_ok=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.best_dir.mkdir(parents=True, exist_ok=True)

    base_config = load_config(args.config)
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
        chunk_config = write_chunk_config(base_config, run_dir, chunk_index, chunk_iters, root)
        train_log = run_dir / f"chunk_{chunk_index:03d}_train.log"
        run_command(["mlx_lm.lora", "--config", str(chunk_config)], train_log, root)

        completed += chunk_iters
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
            record["metrics"] = metrics
            record["score"] = score
            record["collapse_reasons"] = reasons

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
            else:
                record["best_updated"] = False
                record["best_score"] = best_score

            with monitor_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            if reasons:
                best_hint = f"；请使用 best adapter：{best_adapter_path}" if best_metadata else ""
                raise RuntimeError("触发训练停止条件：" + "；".join(reasons) + best_hint)
        else:
            with monitor_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"training finished: {monitor_path}")


if __name__ == "__main__":
    main()
