"""stats 模块的统一可视化输出。

这里会同时生成两大类图片：
1. 基础统计图：轮数分布、token 分布、词数分布、词频图、普通词云
2. 关键词方法图：TF-IDF / TextRank / KeyBERT 的 Top20 图和词云
"""

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from wordcloud import WordCloud

TITLE_SIZE = 22
LABEL_SIZE = 16
TICK_SIZE = 13
OUTPUT_DIRNAME = "vis"
FONT_CANDIDATES = (
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def get_font_path():
    """自动寻找本机可用的中文字体，避免词云乱码。"""
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return font_path
    return None


def ensure_output_dir(base_dir):
    """确保可视化输出目录存在。"""
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def configure_matplotlib(font_path):
    """统一设置 matplotlib 的中文字体和负号显示。"""
    plt.rcParams["axes.unicode_minus"] = False
    if font_path:
        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Heiti SC", "Songti SC"]


def save_histogram(values, title, xlabel, output_path):
    """保存直方图。"""
    plt.figure(figsize=(10, 6))
    plt.hist(values, bins=30, color="#2F6B7C", edgecolor="white")
    plt.title(title, fontsize=TITLE_SIZE)
    plt.xlabel(xlabel, fontsize=LABEL_SIZE)
    plt.ylabel("频数", fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_bar(labels, values, title, xlabel, ylabel, output_path):
    """保存柱状图。"""
    if not labels:
        return
    plt.figure(figsize=(12, 7))
    plt.bar(labels, values, color="#C75B39")
    plt.title(title, fontsize=TITLE_SIZE)
    plt.xlabel(xlabel, fontsize=LABEL_SIZE)
    plt.ylabel(ylabel, fontsize=LABEL_SIZE)
    plt.xticks(rotation=45, ha="right", fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_wordcloud(words, title, output_path, font_path):
    """基于原始词频生成普通词云。"""
    if not words or not font_path:
        return
    cloud = WordCloud(
        width=1400,
        height=900,
        background_color="white",
        font_path=font_path,
        max_words=200,
        collocations=False,
    ).generate(" ".join(words))
    plt.figure(figsize=(14, 9))
    plt.imshow(cloud, interpolation="bilinear")
    plt.axis("off")
    plt.title(title, fontsize=TITLE_SIZE)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def save_keyword_wordcloud(keywords, title, output_path, font_path):
    """基于关键词得分生成“方法词云”。

    这里和普通词云不同，不是直接看出现次数，
    而是把 TF-IDF / TextRank / KeyBERT 的得分当作词云权重。
    """
    if not keywords or not font_path:
        return
    frequencies = {item["token"]: float(item.get("score", item.get("count", 0))) for item in keywords}
    if not frequencies:
        return
    cloud = WordCloud(
        width=1400,
        height=900,
        background_color="white",
        font_path=font_path,
        max_words=200,
        collocations=False,
    ).generate_from_frequencies(frequencies)
    plt.figure(figsize=(14, 9))
    plt.imshow(cloud, interpolation="bilinear")
    plt.axis("off")
    plt.title(title, fontsize=TITLE_SIZE)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def save_method_visuals(split_name, method_name, keywords, output_dir, font_path):
    """为某一种关键词方法生成 Top20 图和词云。"""
    if not keywords:
        return
    labels = [item["token"] for item in keywords[:20]]
    values = [item.get("score", item.get("count", 0)) for item in keywords[:20]]
    method_slug = method_name.lower()
    title_prefix = "全量数据" if split_name == "all" else split_name
    save_bar(
        labels,
        values,
        f"{title_prefix} {method_name} Top20",
        "关键词",
        f"{method_name} 分数",
        output_dir / f"{split_name}_{method_slug}_top20.png",
    )
    save_keyword_wordcloud(
        keywords,
        f"{title_prefix} {method_name} 词云",
        output_dir / f"{split_name}_{method_slug}_wordcloud.png",
        font_path,
    )


def generate_visualizations(basic_results, keyword_results, output_base_dir):
    """执行 stats 全量可视化主流程。"""
    output_dir = ensure_output_dir(output_base_dir)
    font_path = get_font_path()
    configure_matplotlib(font_path)
    all_words = []

    for split_name, metrics in basic_results.items():
        # 基础统计图依赖原始词序列，不依赖某一种关键词算法。
        all_words.extend(metrics["words"])
        counter = Counter(metrics["words"])
        top_words = counter.most_common(20)
        save_histogram(metrics["turn_counts"], f"{split_name} 对话轮数分布", "对话轮数", output_dir / f"{split_name}_turn_count_hist.png")
        save_histogram(metrics["dialogue_token_counts"], f"{split_name} 对话总 token 数分布", "token 数", output_dir / f"{split_name}_dialogue_token_hist.png")
        save_histogram(metrics["dialogue_word_counts"], f"{split_name} 对话总词数分布", "词数", output_dir / f"{split_name}_dialogue_word_hist.png")
        save_bar([item[0] for item in top_words], [item[1] for item in top_words], f"{split_name} 高频词 Top20", "词语", "出现次数", output_dir / f"{split_name}_top_words.png")
        save_wordcloud(metrics["words"], f"{split_name} 词云", output_dir / f"{split_name}_wordcloud.png", font_path)
        # 三种关键词方法都走同一套绘图入口，避免重复写样板代码。
        for method_name, method_results in keyword_results.items():
            save_method_visuals(split_name, method_name, method_results.get(split_name, []), output_dir, font_path)

    all_counter = Counter(all_words)
    all_top_words = all_counter.most_common(20)
    save_bar([item[0] for item in all_top_words], [item[1] for item in all_top_words], "全量数据高频词 Top20", "词语", "出现次数", output_dir / "all_top_words.png")
    save_wordcloud(all_words, "全量数据词云", output_dir / "all_wordcloud.png", font_path)
    for method_name, method_results in keyword_results.items():
        save_method_visuals("all", method_name, method_results.get("all", []), output_dir, font_path)
    if not font_path:
        print("\n未找到可用中文字体，词云图会被跳过。")


def main():
    """允许单独运行 stats 可视化。"""
    from basic_analysis import run_basic_analysis
    from dataloader import load_datasets
    from keybert_analysis import run_keybert_analysis
    from tfidf_analysis import run_advanced_analysis
    from textrank_analysis import run_textrank_analysis

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    basic_results = run_basic_analysis(datasets, current_dir)
    keyword_results = {
        "TFIDF": run_advanced_analysis(basic_results, current_dir),
        "TextRank": run_textrank_analysis(basic_results, current_dir),
        "KeyBERT": run_keybert_analysis(basic_results, current_dir),
    }
    generate_visualizations(basic_results, keyword_results, current_dir)


if __name__ == "__main__":
    main()
