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
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return font_path
    return None


def ensure_output_dir(base_dir):
    output_dir = base_dir / "outputs" / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def configure_matplotlib(font_path):
    plt.rcParams["axes.unicode_minus"] = False
    if font_path:
        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Heiti SC", "Songti SC"]


def save_histogram(values, title, xlabel, output_path):
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


def save_tfidf_wordcloud(keywords, title, output_path, font_path):
    if not keywords or not font_path:
        return

    frequencies = {item["token"]: item["score"] for item in keywords}
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


def generate_visualizations(basic_results, advanced_results, output_base_dir):
    output_dir = ensure_output_dir(output_base_dir)
    font_path = get_font_path()
    configure_matplotlib(font_path)

    all_words = []

    for split_name, metrics in basic_results.items():
        all_words.extend(metrics["words"])
        counter = Counter(metrics["words"])
        top_words = counter.most_common(20)

        save_histogram(
            metrics["turn_counts"],
            f"{split_name} 对话轮数分布",
            "对话轮数",
            output_dir / f"{split_name}_turn_count_hist.png",
        )
        save_histogram(
            metrics["dialogue_token_counts"],
            f"{split_name} 对话总 token 数分布",
            "token 数",
            output_dir / f"{split_name}_dialogue_token_hist.png",
        )
        save_histogram(
            metrics["dialogue_word_counts"],
            f"{split_name} 对话总词数分布",
            "词数",
            output_dir / f"{split_name}_dialogue_word_hist.png",
        )

        save_bar(
            [item[0] for item in top_words],
            [item[1] for item in top_words],
            f"{split_name} 高频词 Top20",
            "词语",
            "出现次数",
            output_dir / f"{split_name}_top_words.png",
        )

        keywords = advanced_results.get(split_name, [])
        save_bar(
            [item["token"] for item in keywords[:20]],
            [item["score"] for item in keywords[:20]],
            f"{split_name} TF-IDF Top20",
            "关键词",
            "TF-IDF 分数",
            output_dir / f"{split_name}_tfidf_top20.png",
        )
        save_tfidf_wordcloud(
            keywords,
            f"{split_name} TF-IDF 词云",
            output_dir / f"{split_name}_tfidf_wordcloud.png",
            font_path,
        )

        save_wordcloud(
            metrics["words"],
            f"{split_name} 词云",
            output_dir / f"{split_name}_wordcloud.png",
            font_path,
        )

    all_counter = Counter(all_words)
    all_top_words = all_counter.most_common(20)
    all_keywords = advanced_results.get("all", [])

    save_bar(
        [item[0] for item in all_top_words],
        [item[1] for item in all_top_words],
        "全量数据高频词 Top20",
        "词语",
        "出现次数",
        output_dir / "all_top_words.png",
    )
    save_bar(
        [item["token"] for item in all_keywords[:20]],
        [item["score"] for item in all_keywords[:20]],
        "全量数据 TF-IDF Top20",
        "关键词",
        "TF-IDF 分数",
        output_dir / "all_tfidf_top20.png",
    )
    save_tfidf_wordcloud(
        all_keywords,
        "全量数据 TF-IDF 词云",
        output_dir / "all_tfidf_wordcloud.png",
        font_path,
    )
    save_wordcloud(
        all_words,
        "全量数据词云",
        output_dir / "all_wordcloud.png",
        font_path,
    )

    if not font_path:
        print("\n未找到可用中文字体，词云图会被跳过。")


def main():
    from advanced_analysis import run_advanced_analysis
    from basic_analysis import run_basic_analysis
    from dataloader import load_datasets

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "CSDS"
    datasets = load_datasets(data_dir)
    basic_results = run_basic_analysis(datasets, current_dir)
    advanced_results = run_advanced_analysis(basic_results, current_dir)
    generate_visualizations(basic_results, advanced_results, current_dir)


if __name__ == "__main__":
    main()
