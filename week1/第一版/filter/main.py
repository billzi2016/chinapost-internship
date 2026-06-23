"""filter 总入口。

顺序固定为：
1. 生成 / 续跑对话 embedding
2. 执行 LLM 二分类过滤
3. 基于 embedding + 过滤结果做降维可视化
"""

from pathlib import Path

from dataloader import load_datasets
from embedding_store import run_embedding_store
from llm_filter import run_llm_filter
from vis import generate_visualizations


def main():
    """执行 filter 目录下的完整主流程。"""
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)

    run_embedding_store(datasets, current_dir)
    run_llm_filter(datasets, current_dir)
    generate_visualizations(current_dir)


if __name__ == "__main__":
    main()
