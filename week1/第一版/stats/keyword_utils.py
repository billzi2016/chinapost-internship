"""关键词分析共用工具。

这里集中维护：
1. 停用词
2. token 规范化逻辑
3. “单条完整对话 = 一个 document”的共用清洗方法
4. 不同分析模块的输出目录创建

这样 TF-IDF / TextRank / KeyBERT 三种方案在清洗口径上保持一致。
"""

TOP_K = 30
MIN_DOC_FREQ = 5
MAX_DOC_FREQ_RATIO = 0.45
STOPWORDS = {
    "的", "了", "是", "吗", "我", "你", "他", "她", "它", "有", "在", "给", "请",
    "还", "什么", "没有", "一个", "这个", "那个", "一下", "一种", "一些", "一下子",
    "一下下", "这样", "那样", "现在", "今天", "明天", "昨天", "这里", "那里", "自己",
    "一下吧", "一下哈", "一下哦", "可能", "因为", "所以", "如果", "但是", "而且", "或者",
    "还是", "然后", "就是", "已经", "还有", "的话", "不用", "需要", "可以", "亲爱",
    "您好呀", "您好呢", "你好呀", "你好呢", "您", "你好", "您好", "好的", "好", "嗯", "呢",
    "哦", "哈", "啊", "呀", "吧", "哦哦", "亲", "亲亲", "请问", "麻烦", "稍等", "收到",
    "知道了", "这边", "那边", "帮", "帮您", "谢谢", "我们", "你们", "他们", "进行", "处理",
    "问题", "咨询", "客户", "用户", "客服", "订单", "京东", "编号", "一下呢", "一下啊",
    "的话呢", "的话哦", "的话哈", "您好亲", "亲们", "小妹", "这会", "目前", "这边呢",
    "那边呢", "申请", "联系", "查询", "订单号",
}
SINGLE_CHAR_STOPWORDS = {
    "不", "为", "下", "到", "对", "就", "会", "要", "再", "能", "可", "把", "让", "从",
    "跟", "被", "将", "向", "和", "及", "与", "或",
}


def normalize_token(token):
    """把原始 token 规范化成更适合关键词分析的形式。"""
    token = token.strip().lower()
    if not token:
        return ""
    if token.startswith("[") and token.endswith("]"):
        return ""
    if token in STOPWORDS or token in SINGLE_CHAR_STOPWORDS:
        return ""
    if len(token) == 1 and not token.isalnum():
        return ""
    if len(token) == 1 and not ("\u4e00" <= token <= "\u9fff"):
        return ""
    if len(token) == 1:
        return ""
    if token.isdigit():
        return ""
    return token


def filter_document(tokens):
    """清洗一条 document 的 token 列表。"""
    return [normalized for token in tokens if (normalized := normalize_token(token))]


def get_all_documents(basic_results):
    """把 train / val / test 三个 split 的 documents 合并成全量列表。"""
    documents = []
    for metrics in basic_results.values():
        documents.extend(metrics.get("documents", []))
    return documents


def ensure_output_dir(base_dir, dirname):
    """创建某一种关键词方法自己的输出目录。"""
    output_dir = base_dir / "outputs" / dirname
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
