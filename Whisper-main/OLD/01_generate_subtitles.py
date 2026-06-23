#!/usr/bin/env python3
"""
使用 mlx-whisper 为视频生成字幕
Apple Silicon 优化版本，使用 MLX 框架
"""

import os
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """检查并安装依赖"""
    try:
        import mlx_whisper
    except ImportError:
        print("正在安装 mlx-whisper...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mlx-whisper"])
        import mlx_whisper
    return mlx_whisper


def find_videos(root_dir: str, extensions: tuple = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv")):
    """递归查找所有视频文件"""
    videos = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(extensions):
                videos.append(Path(root) / file)
    return sorted(videos)


def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def save_srt(segments: list, output_path: Path):
    """保存为 SRT 字幕文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, 1):
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            text = segment["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def transcribe_video(mlx_whisper, video_path: Path, model_name: str = "mlx-community/whisper-large-v3-turbo"):
    """转录单个视频"""
    srt_path = video_path.with_suffix(".srt")

    # 如果字幕已存在，跳过
    if srt_path.exists():
        print(f"  [跳过] 字幕已存在: {srt_path.name}")
        return True

    try:
        print(f"  正在转录...")
        result = mlx_whisper.transcribe(
            str(video_path),
            path_or_hf_repo=model_name,
            verbose=False
        )

        segments = result.get("segments", [])
        if segments:
            save_srt(segments, srt_path)
            print(f"  [完成] 生成字幕: {srt_path.name}")
            return True
        else:
            print(f"  [警告] 未检测到语音")
            return False

    except Exception as e:
        print(f"  [错误] {e}")
        return False


def main():
    # 检查依赖
    print("检查依赖...")
    mlx_whisper = check_dependencies()

    # 设置目录
    root_dir = Path(__file__).parent

    # 查找视频
    print(f"\n在 {root_dir} 中查找视频...")
    videos = find_videos(root_dir)
    print(f"找到 {len(videos)} 个视频文件\n")

    if not videos:
        print("未找到视频文件")
        return

    # 模型选择 (可根据需要修改)
    # 可选模型:
    # - mlx-community/whisper-tiny (最快，准确度较低)
    # - mlx-community/whisper-base
    # - mlx-community/whisper-small
    # - mlx-community/whisper-medium
    # - mlx-community/whisper-large-v3 (最准确，最慢)
    # - mlx-community/whisper-large-v3-turbo (推荐，速度和准确度平衡)
    model_name = "mlx-community/whisper-large-v3-turbo"
    print(f"使用模型: {model_name}\n")

    # 处理视频
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video.relative_to(root_dir)}")

        srt_path = video.with_suffix(".srt")
        if srt_path.exists():
            skip_count += 1
            print(f"  [跳过] 字幕已存在")
            continue

        if transcribe_video(mlx_whisper, video, model_name):
            success_count += 1
        else:
            fail_count += 1

    # 统计
    print(f"\n{'='*50}")
    print(f"处理完成!")
    print(f"  成功: {success_count}")
    print(f"  跳过: {skip_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(videos)}")


if __name__ == "__main__":
    main()
