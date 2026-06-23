#!/usr/bin/env python3
"""
使用 Ollama 将英文字幕翻译成中英双语字幕
"""

import os
import re
from pathlib import Path
import ollama
from tqdm import tqdm


def parse_srt(file_path: Path) -> list:
    """解析 SRT 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 分割字幕块
    blocks = re.split(r'\n\n+', content.strip())
    segments = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text = '\n'.join(lines[2:])
            segments.append({
                'index': index,
                'timestamp': timestamp,
                'text': text
            })

    return segments


def is_bilingual(segments: list) -> bool:
    """检查字幕是否已经是双语"""
    if not segments:
        return False
    # 检查前几个字幕块是否包含中文
    for seg in segments[:5]:
        if re.search(r'[\u4e00-\u9fff]', seg['text']):
            return True
    return False


def translate_text(texts: list, model: str = "gpt-oss:120b") -> list:
    """批量翻译文本"""
    # 将多个文本合并翻译以提高效率
    numbered_texts = [f"{i+1}. {text}" for i, text in enumerate(texts)]
    combined = "\n".join(numbered_texts)

    prompt = f"""这是一个编程算法与系统设计教学视频的字幕。将以下英文字幕翻译成中文。保持编号格式，每行只输出对应的中文翻译，不要输出英文原文。

{combined}"""

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"reasoning_effort": "low"}
    )

    result = response['message']['content'].strip()

    # 解析翻译结果
    translations = []
    lines = result.split('\n')
    for line in lines:
        # 去除编号
        cleaned = re.sub(r'^\d+\.\s*', '', line.strip())
        if cleaned:
            translations.append(cleaned)

    # 确保翻译数量匹配
    while len(translations) < len(texts):
        translations.append(texts[len(translations)])  # 翻译失败则保留原文

    return translations[:len(texts)]


def save_bilingual_srt(segments: list, translations: list, output_path: Path):
    """保存双语字幕文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, (seg, trans) in enumerate(zip(segments, translations)):
            f.write(f"{seg['index']}\n")
            f.write(f"{seg['timestamp']}\n")
            f.write(f"{trans}\n")  # 中文在上
            f.write(f"{seg['text']}\n")  # 英文在下
            f.write("\n")


def find_english_only_srts(root_dir: Path) -> list:
    """查找所有只有英文的 srt 文件"""
    srt_files = []
    for srt_path in root_dir.rglob("*.srt"):
        # 跳过 .en.srt 文件
        if srt_path.stem.endswith('.en'):
            continue
        segments = parse_srt(srt_path)
        if segments and not is_bilingual(segments):
            srt_files.append(srt_path)
    return sorted(srt_files)


def translate_srt(srt_path: Path, model: str = "gpt-oss:120b", batch_size: int = 12):
    """翻译单个 srt 文件"""
    segments = parse_srt(srt_path)
    if not segments:
        tqdm.write(f"  [跳过] 空文件")
        return False

    if is_bilingual(segments):
        tqdm.write(f"  [跳过] 已有双语字幕")
        return False

    # 提取所有文本
    texts = [seg['text'] for seg in segments]

    # 分批翻译
    all_translations = []
    batches = list(range(0, len(texts), batch_size))
    for i in tqdm(batches, desc="  翻译", leave=False):
        batch = texts[i:i+batch_size]
        translations = translate_text(batch, model)
        all_translations.extend(translations)

    # 保存双语字幕（覆盖原文件）
    save_bilingual_srt(segments, all_translations, srt_path)
    tqdm.write(f"  [完成] 已生成双语字幕")
    return True


def main():
    root_dir = Path(__file__).parent
    model = "gpt-oss:120b"

    print(f"使用模型: {model}")
    print(f"查找只有英文的字幕文件...\n")

    srt_files = find_english_only_srts(root_dir)
    print(f"找到 {len(srt_files)} 个需要翻译的字幕文件\n")

    if not srt_files:
        print("所有字幕已经是双语，无需翻译")
        return

    success_count = 0
    fail_count = 0

    for srt_path in tqdm(srt_files, desc="总进度"):
        rel_path = srt_path.relative_to(root_dir)
        tqdm.write(f"\n{rel_path}")

        try:
            if translate_srt(srt_path, model):
                success_count += 1
        except Exception as e:
            tqdm.write(f"  [错误] {e}")
            fail_count += 1

    print(f"\n{'='*50}")
    print(f"翻译完成!")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(srt_files)}")


if __name__ == "__main__":
    main()
