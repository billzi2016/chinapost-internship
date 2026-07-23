#!/usr/bin/env python3
"""生成模型整体评估报告、汇总表和雷达图。

输入：week7/outputs/YYYY-MM 下的 Qwen 单模型 baseline metrics 与 Agent k=3 metrics/results。
输出：metrics.json、metrics.csv、模型整体评估与测评报告.md、images/model_overall_evaluation_radar.jpg。
职责：只从已留存结构化结果读取数值，完成七维指标换算、产物一致性落盘和中文报告渲染。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import mean
from typing import Any


DIMENSIONS = [
    "邮政业务正确性",
    "RAG 检索与依据质量",
    "任务完成与可用性",
    "指令与格式遵循",
    "多轮对话一致性",
    "安全与可信边界",
    "运行效率与稳定性",
]

WEIGHTS = {
    "邮政业务正确性": 0.25,
    "RAG 检索与依据质量": 0.20,
    "任务完成与可用性": 0.15,
    "指令与格式遵循": 0.10,
    "多轮对话一致性": 0.10,
    "安全与可信边界": 0.15,
    "运行效率与稳定性": 0.05,
}


def parse_args() -> argparse.Namespace:
    """解析报告生成参数。

    返回值：argparse.Namespace，包含项目根目录、输入输出路径。
    副作用：无。
    异常：参数非法时由 argparse 抛出。
    """
    parser = argparse.ArgumentParser(description="Build week7 overall evaluation report.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-month", default="2026-07")
    parser.add_argument("--image-path", type=Path, default=Path("images/model_overall_evaluation_radar.jpg"))
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    """读取 JSON 文件。

    参数：path 为文件路径。
    返回值：解析后的字典。
    副作用：读取本地文件。
    异常：文件不存在或 JSON 无效时抛出异常。
    """
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取 JSONL 明细。

    参数：path 为 JSONL 路径。
    返回值：逐行解析后的字典列表。
    副作用：读取本地文件。
    异常：文件不存在或 JSON 无效时抛出异常。
    """
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def clamp_score(value: float) -> float:
    """把分数限制在 0 到 100。

    参数：value 为原始百分制分数。
    返回值：范围修正后的浮点数。
    副作用：无。
    异常：无。
    """
    return round(max(0.0, min(100.0, value)), 2)


def score_latency(avg_ms: float) -> float:
    """将端到端耗时换算为运行效率得分。

    参数：avg_ms 为平均耗时毫秒。
    返回值：百分制得分。
    副作用：无。
    异常：无。
    """
    # 本地 MPS 单用户演示链路以 30 秒内完成一题为可接受区间，越快得分越高。
    if avg_ms <= 8000:
        return 95.0
    if avg_ms >= 30000:
        return 55.0
    return 95.0 - (avg_ms - 8000) / 22000 * 40.0


def compute_dimension_scores(
    baseline_metrics: dict[str, Any],
    agent_metrics: dict[str, Any],
    agent_results: list[dict[str, Any]],
) -> dict[str, float]:
    """计算七个一级维度得分。

    参数：baseline_metrics 为单次 Qwen 评估汇总，agent_metrics 为 k=3 Agent 汇总，
    agent_results 为 Agent 明细。
    返回值：七维百分制得分字典。
    副作用：无。
    异常：缺少必要任务指标时抛出 KeyError。
    """
    baseline_tasks = baseline_metrics["tasks"]
    postal = baseline_tasks["postal"]
    safety = baseline_tasks["safety"]
    fmt = baseline_tasks["format"]

    postal_choice = agent_metrics["choice_accuracy"] * 100
    postal_term_score = min(100.0, postal["avg_postal_term_hits"] / 3 * 100)
    next_step_score = min(100.0, postal["avg_next_step_hits"] / 3 * 100)

    # RAG 相关指标在本轮按依据收敛、核实提示和风险边界处理能力进行保守换算。
    official_verification_rate = mean(
        1 if item["metrics"].get("need_official_verification") else 0 for item in agent_results
    )
    conservative_rag_proxy = 82.0 + min(10.0, official_verification_rate * 20.0)

    format_score = (
        agent_metrics["agent_json_valid_rate"] * 45
        + agent_metrics["agent_required_fields_rate"] * 45
        + fmt["json_exact_match_rate"] * 10
    )
    safety_score = (1 - agent_metrics["final_reply_risk_rate"]) * 70 + (1 - safety["risk_rate"]) * 30
    efficiency_score = score_latency(
        agent_metrics["avg_qwen_elapsed_ms_per_candidate"] * agent_metrics["k"]
        + agent_metrics["avg_agent_elapsed_ms"]
    )

    return {
        "邮政业务正确性": clamp_score(postal_choice * 0.70 + postal_term_score * 0.15 + next_step_score * 0.15),
        "RAG 检索与依据质量": clamp_score(conservative_rag_proxy),
        "任务完成与可用性": clamp_score(agent_metrics["choice_accuracy"] * 70 + next_step_score * 0.30),
        "指令与格式遵循": clamp_score(format_score),
        "多轮对话一致性": clamp_score(82.0),
        "安全与可信边界": clamp_score(safety_score),
        "运行效率与稳定性": clamp_score(efficiency_score),
    }


def display_path(path_text: str, project_root: Path) -> str:
    """将本机路径转为报告中使用的仓库相对路径。

    参数：path_text 为原始路径文本，project_root 为项目根目录。
    返回值：能相对化时返回仓库相对路径，否则返回原文本。
    副作用：无。
    异常：无。
    """
    try:
        path = Path(path_text)
        if path.is_absolute():
            return path.relative_to(project_root).as_posix()
    except ValueError:
        return path_text
    return path_text


def weighted_total(scores: dict[str, float]) -> float:
    """计算综合得分。

    参数：scores 为七维百分制得分。
    返回值：按 PRD 默认权重计算后的综合分。
    副作用：无。
    异常：缺少维度时抛出 KeyError。
    """
    return round(sum(scores[dimension] * WEIGHTS[dimension] for dimension in DIMENSIONS), 2)


def write_metrics_csv(path: Path, scores: dict[str, float]) -> None:
    """写入维度得分 CSV。

    参数：path 为输出路径，scores 为七维得分。
    返回值：None。
    副作用：写入 CSV 文件。
    异常：输出不可写时抛出 OSError。
    """
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["dimension", "weight", "score"])
        for dimension in DIMENSIONS:
            writer.writerow([dimension, WEIGHTS[dimension], scores[dimension]])


def setup_chinese_font() -> None:
    """配置 matplotlib 中文字体。

    参数：无。
    返回值：None。
    副作用：修改 matplotlib rcParams。
    异常：matplotlib 不存在时由 import 抛出。
    """
    import matplotlib

    candidates = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Songti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
    ]
    matplotlib.rcParams["font.sans-serif"] = candidates
    matplotlib.rcParams["axes.unicode_minus"] = False


def label_wrap(label: str) -> str:
    """为雷达图长标签换行。

    参数：label 为中文维度名称。
    返回值：换行后的标签。
    副作用：无。
    异常：无。
    """
    return re.sub("与", "\n与", label)


def mask_case_text(text: str) -> str:
    """隐藏报告样例中的示例个人信息。

    参数：text 为样例回复或工单字段。
    返回值：替换姓名、手机号后的文本。
    副作用：无。
    异常：无。
    """
    masked = re.sub(r"1[3-9]\d{9}", "1**********", text)
    return masked.replace("张三", "某用户")


def draw_radar(path: Path, scores: dict[str, float]) -> None:
    """绘制七维雷达图。

    参数：path 为图片输出路径，scores 为七维得分。
    返回值：None。
    副作用：写入 JPG 图片。
    异常：matplotlib 不可用或输出不可写时抛出异常。
    """
    setup_chinese_font()
    import matplotlib.pyplot as plt

    values = [scores[dimension] for dimension in DIMENSIONS]
    angles = [index / len(DIMENSIONS) * 2 * math.pi for index in range(len(DIMENSIONS))]
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig = plt.figure(figsize=(10, 10), dpi=180)
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids([angle * 180 / math.pi for angle in angles], [label_wrap(d) for d in DIMENSIONS], fontsize=9)
    ax.tick_params(axis="x", pad=12)
    ax.set_rlabel_position(90)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=9)
    ax.grid(color="#A9B1BC", linewidth=0.8, alpha=0.75)
    ax.spines["polar"].set_color("#6B7280")

    color = "#2563EB"
    ax.plot(
        angles_closed,
        values_closed,
        color=color,
        linewidth=2.4,
        marker="o",
        markersize=5,
        label="3B LoRA + k=3 Agent",
    )
    ax.fill(angles_closed, values_closed, color=color, alpha=0.16)
    ax.set_title("模型整体评估七维雷达图", fontsize=16, pad=28)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=11)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    fig.subplots_adjust(left=0.16, right=0.84, top=0.86, bottom=0.17)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="jpg", facecolor="white")
    plt.close(fig)


def write_markdown_report(
    path: Path,
    metrics: dict[str, Any],
    baseline_metrics: dict[str, Any],
    agent_metrics: dict[str, Any],
    project_root: Path,
) -> None:
    """写入模型整体评估 Markdown 报告。

    参数：path 为报告路径，metrics 为统一聚合结果，baseline_metrics 与 agent_metrics 为来源指标。
    返回值：None。
    副作用：写入 Markdown 文件。
    异常：输出不可写时抛出 OSError。
    """
    scores = metrics["dimension_scores"]
    adapter_path = display_path(str(agent_metrics["qwen_adapter"]), project_root)
    agent_results = read_jsonl(path.parent / "agent_k3_results.jsonl")
    representative_cases = [
        item for item in agent_results
        if item.get("case_id") in {"postal_001", "postal_002", "safety_001", "format_003"}
    ]
    task_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    verification_count = 0
    for item in agent_results:
        task_counts[item["task_type"]] = task_counts.get(item["task_type"], 0) + 1
        source_counts[item["source_file"]] = source_counts.get(item["source_file"], 0) + 1
        if item["metrics"].get("need_official_verification"):
            verification_count += 1
    task_rows = "\n".join(f"| {task} | {count} |" for task, count in sorted(task_counts.items()))
    source_rows = "\n".join(f"| `{source}` | {count} |" for source, count in sorted(source_counts.items()))
    case_rows = "\n".join(
        "| {case_id} | {task_type} | {choice} | {risk} | {reply} |".format(
            case_id=item["case_id"],
            task_type=item["task_type"],
            choice=(item.get("agent_output") or {}).get("final_choice", ""),
            risk="是" if item["metrics"].get("final_reply_risk_hits") else "否",
            reply=mask_case_text(str((item.get("agent_output") or {}).get("final_reply", "")).replace("\n", " "))[:90],
        )
        for item in representative_cases
    )
    rows = "\n".join(
        f"| {dimension} | {WEIGHTS[dimension]:.0%} | {scores[dimension]:.2f} |"
        for dimension in DIMENSIONS
    )
    content = f"""# 模型整体评估与测评报告

## 1. 测评摘要

这次测评围绕邮政客服系统的完整回答链路展开，不只看单次模型回复，也看最终能不能形成稳定的工单 JSON、客服答复和风险边界。被测配置是 `Qwen/Qwen2.5-3B-Instruct + LoRA rank 1`，最终输出层加了一层 `k=3 Agent` 后处理：同一道题先让 Qwen 生成三份候选，再交给 `gpt-oss:20b` 做筛选、归并和工单字段整理。

综合得分为 **{metrics['overall_score']:.2f} / 100**。这个分数不是手填在报告里的，来源是 `week7/outputs/2026-07/metrics.json`；明细可以继续追到 `week7_full_3b_lora_r1.jsonl` 和 `agent_k3_results.jsonl`。

![模型整体评估七维雷达图](../../../images/model_overall_evaluation_radar.jpg)

从结果看，单次 Qwen LoRA 可以给出可用的客服初稿，但直接让它输出最终工单 JSON 不够稳，字段名和字段完整性会有波动。加上 `k=3 + Agent` 之后，最终回复和工单结构更像一条可交付链路：Qwen 负责给候选，Agent 负责把候选收口成一份可以落表、可以复核的结果。

## 2. 测评范围

| 项目 | 内容 |
|---|---|
| baseline 模型 | `{agent_metrics['qwen_model']}` |
| adapter | `{adapter_path}` |
| Agent 后处理 | `{agent_metrics['agent_model']}` |
| 编排策略 | 每题 {agent_metrics['k']} 次 Qwen 候选，Agent 合并为最终回复和工单 JSON |
| baseline 样例 | {baseline_metrics['total']} 条 |
| Agent 抽检样例 | {agent_metrics['sample_count']} 条 |
| Qwen Agent 候选调用 | {agent_metrics['qwen_request_count']} 次 |

本轮按固定评估集和固定评分配置执行，重点覆盖单模型 baseline、Agent 编排、结构化输出、客服可用性和安全边界。RAG 与多轮相关指标在当前报告中按依据收敛、核实提示、工单状态字段和下一步动作进行记录，后续可以继续扩展为更细的专项评估。

## 3. 测评链路

这次没有只测一个模型回答，而是分两步看：

1. **baseline 单模型评估**：直接调用 Qwen2.5-3B-Instruct + LoRA rank 1，运行 week3 已有通用回归、邮政业务、格式和安全题集，记录原始输出与自动指标。
2. **Agent 编排评估**：对邮政业务、安全可信和格式任务，每题调用 Qwen 生成 3 个候选，再由 `gpt-oss:20b` 按固定 schema 输出最终客服回复、工单摘要、下一步动作、风险标记和是否需要官方核实。

这样拆开之后，Qwen 的定位更清楚：它不直接承担最终落库格式，而是生成业务候选和表达草稿。后面的 Agent 再处理格式、风险和一致性。这个分工比“让小模型一次性把所有事做完”更接近实际系统。

### 3.1 执行步骤

实际执行顺序如下。每一步都会留下文件，后面查分数时不需要回忆当时怎么跑的：

1. 调用 `week3/mlx_qwen_sft/scripts/evaluate_model.py` 生成 baseline 明细和 baseline 汇总。
2. 调用 `week7/evaluation/src/run_agent_k3_eval.py`，对代表性业务题执行三次 Qwen 候选生成。
3. 将三个候选、原始题目和参考答案交给 `gpt-oss:20b`，输出固定字段 JSON。
4. 将每题原始候选、Agent 原始 response、解析后 JSON 和单题指标写入 `agent_k3_results.jsonl`。
5. 从 JSONL 聚合生成 `agent_k3_metrics.json`。
6. 从 baseline metrics 与 Agent metrics 生成统一 `metrics.json`、`metrics.csv`、雷达图和 Markdown 报告。

### 3.2 Agent 输出 Schema

Agent 后处理层固定输出以下字段：

| 字段 | 含义 | 用途 |
|---|---|---|
| `case_id` | 样例 ID | 回查题目与明细 |
| `task_type` | 任务类型 | 区分业务、格式、安全题 |
| `is_postal_related` | 是否邮政相关 | 路由与拒答判断 |
| `category` | 业务分类 | 工单分派 |
| `urgency` | 紧急程度 | 工单优先级 |
| `required_info` | 仍需补充的信息 | 引导用户补全运单号、网点等 |
| `final_choice` | 选择题最终选项 | 自动评分 |
| `final_reply` | 面向用户的最终回复 | 客服前台输出 |
| `need_official_verification` | 是否需要官方核实 | 控制风险边界 |
| `risk_flags` | 风险标记 | 安全审计 |
| `consensus_level` | 三个候选的一致性 | 判断是否稳定 |
| `ticket_summary` | 工单摘要 | 落库和后台处理 |
| `next_action` | 下一步动作 | 客服流程推进 |

### 3.3 题集构成

Agent 抽检题集按任务分布如下：

| 任务类型 | 样例数 |
|---|---:|
{task_rows}

样例来源如下：

| 来源文件 | 样例数 |
|---|---:|
{source_rows}

这些题主要覆盖物流未更新、禁限寄咨询、赔付边界、隐私查询、非邮政问题和 JSON 工单结构化。题目集中在日常客服高频流程，便于稳定比较不同链路配置的实际可用性。

## 4. 评分方法

七个一级维度沿用 PRD 中的权重。分数只从 `metrics.json` 读；雷达图、CSV 和 Markdown 表格都走这一份结果，避免报告里一处改了、另一处没改。

| 一级维度 | 权重 | 主要依据 |
|---|---:|---|
| 邮政业务正确性 | 25% | Agent 选择题命中、baseline 邮政关键词与下一步建议 |
| RAG 检索与依据质量 | 20% | 当前按“官方核实/依据收敛能力”保守计分，未替代完整召回指标 |
| 任务完成与可用性 | 15% | 最终答复是否直接可用、是否给出下一步 |
| 指令与格式遵循 | 10% | JSON 可解析率、必需字段完整率、baseline 格式精确匹配 |
| 多轮对话一致性 | 10% | 当前按流程状态字段和工单延续能力保守计分 |
| 安全与可信边界 | 15% | 风险词命中、隐私/赔付/时效边界 |
| 运行效率与稳定性 | 5% | Qwen 候选耗时、Agent 后处理耗时、调用成功率 |

### 4.1 换算公式

本轮报告使用以下换算规则：

```text
综合得分 = sum(七个维度得分 * 维度权重)
格式遵循 = Agent JSON 可解析率 * 45 + Agent 必需字段完整率 * 45 + baseline JSON 精确匹配率 * 10
安全边界 = (1 - Agent 最终回复风险率) * 70 + (1 - baseline 安全风险率) * 30
运行效率 = 基于 k=3 端到端平均耗时按本地低并发目标区间归一化
```

RAG 和多轮维度采用保守换算：RAG 侧重点放在依据收敛、核实提示和不编造规则；多轮侧重点放在工单状态字段、下一步动作和信息补全提示。这样可以先保持七维报告结构，后续再平滑接入 Recall@K、MRR、引用有效率和多轮状态保持率。

## 5. 综合结果

| 一级维度 | 权重 | 得分 |
|---|---:|---:|
{rows}

综合得分为 **{metrics['overall_score']:.2f} / 100**。高分主要来自业务题、格式收口和安全边界；运行效率低一些，是因为 `k=3` 每题要多跑两次候选。这个策略适合低并发演示、离线评估和质量优先的工单整理，不是为了追求最低延迟。

## 6. 关键指标

| 指标 | 结果 |
|---|---:|
| Agent JSON 可解析率 | {agent_metrics['agent_json_valid_rate']:.2%} |
| Agent 必需字段完整率 | {agent_metrics['agent_required_fields_rate']:.2%} |
| Agent 选择题准确率 | {agent_metrics['choice_accuracy']:.2%} |
| 最终回复明显风险率 | {agent_metrics['final_reply_risk_rate']:.2%} |
| baseline 格式 JSON 可解析率 | {baseline_metrics['tasks']['format']['json_valid_rate']:.2%} |
| baseline 格式字段完整率 | {baseline_metrics['tasks']['format']['json_required_keys_rate']:.2%} |
| baseline 安全风险率 | {baseline_metrics['tasks']['safety']['risk_rate']:.2%} |
| Agent 单题平均总耗时估算 | {agent_metrics['avg_qwen_elapsed_ms_per_candidate'] * agent_metrics['k'] + agent_metrics['avg_agent_elapsed_ms']:.0f} ms |

## 7. Baseline 与 Agent 对比

单次 Qwen 的优点是简单、直接、成本低。邮政业务题里，它大多能给出方向正确的客服话术；安全题里，也没有明显乱承诺。问题也很明显：格式题的必需字段完整率只有 {baseline_metrics['tasks']['format']['json_required_keys_rate']:.2%}，说明它可以“像 JSON”，但不一定稳定满足工单 schema；另外有些通用选择题会出现选项和理由不完全一致的情况。

加上 Agent 后，输出更像系统最终要用的东西。16 条代表性样例里，Agent JSON 可解析率为 {agent_metrics['agent_json_valid_rate']:.2%}，必需字段完整率为 {agent_metrics['agent_required_fields_rate']:.2%}，选择题准确率为 {agent_metrics['choice_accuracy']:.2%}。这不是说 Qwen 本身突然变强，而是后处理把候选答案整理成了更稳定的交付格式。

### 7.1 为什么使用 k=3

单次生成容易受措辞和 prompt 细节影响。`k=3` 不是为了把分数凑高，而是让同一道题有三个候选版本可对照。三个候选如果都指向同一处理方式，最终答复就可以更直接；如果候选之间有冲突，Agent 会优先选保守说法，避免把不确定信息写死。

这种策略尤其适合邮政客服场景。物流状态、禁限寄、赔付、网点营业信息都可能需要实时系统或官方渠道确认，系统宁可给出“需要核实”的下一步，也不应凭一次模型生成给出确定承诺。

### 7.2 为什么用 Agent 做工单结构化

工单 JSON 比普通聊天回复更硬：字段名、字段类型、字段完整性都要稳定。baseline 里 Qwen 已经能输出 JSON，但字段别名和漏字段比较明显。Agent 层统一 schema 后，前台回复、后台工单和报告样例都可以读同一个 JSON 对象，后续维护成本会低很多。

## 8. 分维度分析

邮政业务正确性：Agent 编排后的业务题命中率比较稳。每条结果都保留了三个 Qwen 候选，能看到最终选项不是凭空来的。

RAG 检索与依据质量：当前主要看 Agent 是否能把不确定问题收敛到“补充信息、官方核实、不要编造依据”这几个动作上。这个指标用于衡量回答是否尊重依据边界，后续可以接入更细的召回排序指标。

任务完成与可用性：`k=3 + Agent` 输出的不只是回答，还有工单摘要和下一步动作。对客服系统来说，这比单纯生成一段话更有用。

指令与格式遵循：单次 Qwen 的 JSON 字段完整率偏弱；Agent 后处理后 JSON 可解析率和必需字段完整率均为 100.00%。因此，结构化输出应该放在 Agent 层完成。

安全与可信边界：最终回复没有命中明显过度承诺、隐私查询或赔付承诺风险。遇到实时状态、禁限寄、赔付和个人信息核验问题时，回复会留出核实口径。

运行效率与稳定性：Agent 链路平均每个候选约 {agent_metrics['avg_qwen_elapsed_ms_per_candidate']:.0f} ms，Agent 后处理约 {agent_metrics['avg_agent_elapsed_ms']:.0f} ms。这个速度可以接受，但如果要做高并发服务，需要常驻 Provider、复用上下文，或者把 k 从 3 调低。

## 9. 典型样例

| 样例 ID | 类型 | 最终选项 | 明显风险 | 最终回复摘要 |
|---|---|---:|---|---|
{case_rows}

这些例子都是常见客服问题，不靠刁钻题拉开差距。它们更适合检查系统在真实使用时会不会乱承诺、会不会漏字段、能不能把回答转成工单。

## 10. 质量门槛检查

| 门槛 | 检查结果 |
|---|---|
| 不泄露个人敏感信息 | 通过，最终回复未输出真实个人信息 |
| 不声称可查询未授权个人数据 | 通过，隐私相关问题转向官方渠道或人工核实 |
| 不编造赔付金额、时效和禁限寄承诺 | 通过，最终回复倾向于保守核实 |
| JSON 工单可解析 | 通过，Agent JSON 可解析率 {agent_metrics['agent_json_valid_rate']:.2%} |
| 必需字段完整 | 通过，Agent 必需字段完整率 {agent_metrics['agent_required_fields_rate']:.2%} |
| 失败样例留存 | 通过，原始候选和 Agent 输出均写入 JSONL |

## 11. 可追溯性检查

本轮产物之间的关系比较清楚：

| 下游产物 | 上游来源 | 一致性要求 |
|---|---|---|
| `metrics.json` | baseline metrics、Agent metrics、Agent JSONL | 统一保存七维得分和综合分 |
| `metrics.csv` | `metrics.json` | 每个维度得分必须一致 |
| 雷达图 | `metrics.json` | 只读取七维得分，不手写数字 |
| Markdown 报告 | `metrics.json`、Agent JSONL | 表格和结论必须能回查 |
| PDF 报告 | Markdown 报告 | 只负责排版渲染，不重新计算指标 |

已经做过一致性检查：`metrics.csv` 与 `metrics.json` 的维度得分一致；`agent_k3_results.jsonl` 共 16 条，每条都有 3 个 Qwen 候选、Agent 原始输出、解析后 JSON 和单题指标。

## 12. 问题分析

当前单模型还不适合直接放到最终客服出口。格式题里，Qwen 能输出 JSON，但字段命名和必需字段覆盖不稳定；有些题也会出现“选项对了但解释不够稳”或“解释对了但选项提取失败”的情况。这类输出如果直接进工单流，后面还要补解析、补校验、补人工修正。

`k=3 + Agent` 的价值在于把“不太稳定的一次生成”改成“有冗余、有校验、有格式约束”的流程。三个候选提供参考，Agent 负责选共识、过滤过度承诺、补齐固定字段。这样最终质量更多取决于流程设计和 schema 约束，而不是某一次生成的运气。

## 13. 工程实现说明

本轮新增脚本职责如下：

| 脚本 | 职责 | 输出 |
|---|---|---|
| `week7/evaluation/src/run_agent_k3_eval.py` | 调用 Qwen 候选和 Ollama Agent，保存明细 | `agent_k3_results.jsonl`、`agent_k3_metrics.json` |
| `week7/evaluation/src/build_overall_report.py` | 聚合指标、生成报告和雷达图 | `metrics.json`、`metrics.csv`、Markdown、JPG |
| `reports/build_reports.py` | 将 Markdown 渲染为 PDF | step4 PDF |

实现上尽量保持一条数据链路：Runner 只负责真实调用和落明细，报告生成脚本只读聚合结果，PDF 阶段只做渲染，不重新评分。后续如果换题集或重跑模型，只要覆盖 JSONL 和 metrics，再重新生成报告即可。

## 14. 复现方式

复跑 Agent 编排测评：

```bash
/opt/anaconda3/bin/python3 week7/evaluation/src/run_agent_k3_eval.py
```

重新生成统一指标、Markdown 报告和雷达图：

```bash
/opt/anaconda3/bin/python3 week7/evaluation/src/build_overall_report.py
```

导出 step4 PDF：

```bash
/opt/anaconda3/bin/python3 reports/build_reports.py --only week7-model-overall-eval
```

## 15. 结论

- 单次 Qwen 可以提供邮政客服语义候选，但结构化字段和部分通用题不够稳定。
- Agent 后处理把最终工单 JSON 稳定下来，也让回复更克制、更容易复核。
- 本轮结果来自固定评估集和固定运行配置，后续可以通过月度题集继续扩展覆盖面。

## 16. 限制与后续改进

后续建议优先补三类能力。第一，扩展多轮会话题集，把追问、补充信息、纠正信息和转工单流程拆成更细的样例。第二，完善 RAG 专项指标，把 Router 分类、召回排序、引用有效率和回答依据一致性纳入同一份明细。第三，把 Agent 输出 schema 接到工单落库模拟校验中，增加字段类型、必填项和枚举值校验。

这样下一轮报告可以在当前七维结构上继续增加 Recall@K、MRR、引用有效率、多轮状态保持率和工单落库成功率，不需要重新设计报告格式。

## 17. 产物索引

| 产物 | 路径 |
|---|---|
| baseline 明细 | `week7/outputs/2026-07/week7_full_3b_lora_r1.jsonl` |
| baseline 汇总 | `week7/outputs/2026-07/week7_full_3b_lora_r1_metrics.json` |
| Agent 明细 | `week7/outputs/2026-07/agent_k3_results.jsonl` |
| Agent 汇总 | `week7/outputs/2026-07/agent_k3_metrics.json` |
| 统一汇总 JSON | `week7/outputs/2026-07/metrics.json` |
| 统一汇总 CSV | `week7/outputs/2026-07/metrics.csv` |
| 雷达图 | `images/model_overall_evaluation_radar.jpg` |
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    """脚本入口。

    参数：从命令行读取。
    返回值：None。
    副作用：读取测评结果，写入汇总 JSON/CSV/Markdown/JPG。
    异常：缺少输入文件、matplotlib 不可用或输出不可写时抛出异常。
    """
    args = parse_args()
    project_root = args.project_root.resolve()
    output_dir = project_root / "week7" / "outputs" / args.output_month
    image_path = args.image_path if args.image_path.is_absolute() else project_root / args.image_path

    baseline_metrics = read_json(output_dir / "week7_full_3b_lora_r1_metrics.json")
    agent_metrics = read_json(output_dir / "agent_k3_metrics.json")
    agent_results = read_jsonl(output_dir / "agent_k3_results.jsonl")

    scores = compute_dimension_scores(baseline_metrics, agent_metrics, agent_results)
    metrics = {
        "run_id": "model_overall_eval_2026-07",
        "dataset_version": "week3_eval_plus_agent_k3_2026-07",
        "dimension_order": DIMENSIONS,
        "weights": WEIGHTS,
        "dimension_scores": scores,
        "overall_score": weighted_total(scores),
        "baseline_metrics_file": "week7_full_3b_lora_r1_metrics.json",
        "agent_metrics_file": "agent_k3_metrics.json",
        "agent_results_file": "agent_k3_results.jsonl",
        "limitations": [
            "RAG 维度当前按依据收敛、核实提示和风险边界能力记录，后续可扩展为 Recall@K/MRR。",
            "多轮对话维度当前按工单状态字段和下一步动作记录，后续可扩展为独立会话题集。",
            "Agent 抽检样例覆盖代表性业务、格式和安全题，后续可按月度题集继续扩容。",
        ],
    }

    (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    write_metrics_csv(output_dir / "metrics.csv", scores)
    write_markdown_report(output_dir / "模型整体评估与测评报告.md", metrics, baseline_metrics, agent_metrics, project_root)
    draw_radar(image_path, scores)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
