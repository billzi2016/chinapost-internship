#!/usr/bin/env python3
"""
将双语字幕拆分成独立的中文和英文字幕文件
"""

import re
from pathlib import Path
from tqdm import tqdm


def parse_srt(file_path: Path) -> list:
    """解析 SRT 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r'\n\n+', content.strip())
    segments = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text_lines = lines[2:]
            segments.append({
                'index': index,
                'timestamp': timestamp,
                'text_lines': text_lines
            })

    return segments


def has_chinese(text: str) -> bool:
    """检查文本是否包含中文"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def is_bilingual(segments: list) -> bool:
    """检查字幕是否是双语"""
    if not segments:
        return False
    # 检查前几个字幕块
    for seg in segments[:5]:
        if len(seg['text_lines']) >= 2:
            has_zh = any(has_chinese(line) for line in seg['text_lines'])
            has_en = any(not has_chinese(line) and line.strip() for line in seg['text_lines'])
            if has_zh and has_en:
                return True
    return False


def split_text_lines(text_lines: list) -> tuple:
    """将文本行分成中文和英文"""
    zh_lines = []
    en_lines = []

    for line in text_lines:
        if has_chinese(line):
            zh_lines.append(line)
        else:
            en_lines.append(line)

    return '\n'.join(zh_lines), '\n'.join(en_lines)


def save_srt(segments: list, output_path: Path, lang: str):
    """保存字幕文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"{seg['index']}\n")
            f.write(f"{seg['timestamp']}\n")
            f.write(f"{seg[lang]}\n")
            f.write("\n")


def split_srt(srt_path: Path) -> bool:
    """拆分单个双语字幕文件"""
    segments = parse_srt(srt_path)

    if not segments:
        tqdm.write(f"  [跳过] 空文件")
        return False

    if not is_bilingual(segments):
        tqdm.write(f"  [跳过] 不是双语字幕")
        return False

    # 分离中英文
    for seg in segments:
        zh_text, en_text = split_text_lines(seg['text_lines'])
        seg['zh'] = zh_text
        seg['en'] = en_text

    # 生成文件路径
    stem = srt_path.stem
    parent = srt_path.parent
    zh_path = parent / f"{stem}.zh.srt"
    en_path = parent / f"{stem}.en.srt"

    # 保存
    save_srt(segments, zh_path, 'zh')
    save_srt(segments, en_path, 'en')

    # 删除原文件
    srt_path.unlink()

    tqdm.write(f"  [完成] -> {zh_path.name}, {en_path.name}")
    return True


def find_bilingual_srts(root_dir: Path) -> list:
    """查找所有双语字幕文件"""
    srt_files = []
    for srt_path in root_dir.rglob("*.srt"):
        # 跳过已经拆分的文件
        if srt_path.stem.endswith('.zh') or srt_path.stem.endswith('.en'):
            continue
        segments = parse_srt(srt_path)
        if segments and is_bilingual(segments):
            srt_files.append(srt_path)
    return sorted(srt_files)


def main():
    root_dir = Path(__file__).parent

    print("查找双语字幕文件...\n")

    srt_files = find_bilingual_srts(root_dir)
    print(f"找到 {len(srt_files)} 个双语字幕文件\n")

    if not srt_files:
        print("没有找到需要拆分的双语字幕")
        return

    success_count = 0
    fail_count = 0

    for srt_path in tqdm(srt_files, desc="总进度"):
        rel_path = srt_path.relative_to(root_dir)
        tqdm.write(f"\n{rel_path}")

        try:
            if split_srt(srt_path):
                success_count += 1
        except Exception as e:
            tqdm.write(f"  [错误] {e}")
            fail_count += 1

    print(f"\n{'='*50}")
    print(f"拆分完成!")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(srt_files)}")


if __name__ == "__main__":
    main()
