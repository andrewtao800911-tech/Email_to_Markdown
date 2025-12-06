#!/usr/bin/env python3
"""
clean_md.py

清理 Markdown 文件：
1. 删除所有空行
2. 删除仅包含符号或空白的行（无中日文/英文/数字）
3. 删除行尾多余空格
4. 处理以">"开头的引用行
5. 可选：压缩行内多个连续空格为一个 (--strip-all-spaces)

用法示例:
    python 06_clean_md.py --src data/05_Split_History --dst data/06_Cleaned
    python 06_clean_md.py --src data/05_Split_History --dst data/06_Cleaned --strip-all-spaces
"""

import re
import sys
from pathlib import Path

# 导入配置和日志管理模块
try:
    from config import get_step_config
    from logging_utils import get_logger
    from directory_manager import get_directory_manager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py、logging_utils.py和directory_manager.py文件在当前目录或Python路径中")
    sys.exit(1)

# 匹配包含有意义字符（中、日、英文、数字）的行
MEANINGFUL_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff\u3040-\u30ff\u3400-\u4dbf]")

# 匹配以一个或多个">"开头且">"之间可能包含空格的行
QUOTE_PATTERN = re.compile(r"^(> *)+(.*)$")

def clean_text(text: str, strip_all_spaces: bool = False) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        # 处理以">"开头的引用行
        quote_match = QUOTE_PATTERN.match(line)
        if quote_match:
            # 提取">"后的文本内容
            content = quote_match.group(2)
            if not content.strip():
                # 如果">"后只有空格或为空，则删除整行
                continue
            elif MEANINGFUL_PATTERN.search(content):
                # 如果">"后有有意义的文字内容，则保留文字部分
                line = content
            else:
                # 如果">"后只有符号而没有文字内容，则删除整行
                continue

        if not line.strip():
            continue  # 删除空行
        if not MEANINGFUL_PATTERN.search(line):
            continue  # 删除纯符号行

        # 去掉行尾多余空格
        line = line.rstrip()

        if strip_all_spaces:
            # 保留行首缩进，压缩行内多余空格
            indent = len(line) - len(line.lstrip(" "))
            core = re.sub(r"\s{2,}", " ", line.lstrip(" "))
            line = " " * indent + core

        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def process_file(md_path: Path, src_root: Path, dst_root: Path, strip_all_spaces: bool, logger, dir_manager):
    rel_path = md_path.relative_to(src_root)
    dst_path = dst_root / rel_path
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    text = md_path.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_text(text, strip_all_spaces=strip_all_spaces)
    dst_path.write_text(cleaned, encoding="utf-8")
    
    # 记录文件操作
    logger.info(f"清理文件: {md_path.relative_to(src_root)} -> {dst_path.relative_to(dst_root)}")
    
    return dst_path

def process_dir(src_root: Path, dst_root: Path, strip_all_spaces: bool):
    # 获取步骤配置
    step_config = get_step_config("06")
    
    # 初始化日志记录器
    logger = get_logger("06_clean_md")
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("06")
    
    # 开始步骤
    logger.log_start()
    
    # 确保输出目录存在
    dir_manager.ensure_directory_exists(dst_root)
    
    # 统计处理的文件数量
    processed_count = 0
    
    for md_path in src_root.rglob("*.md"):
        out_path = process_file(md_path, src_root, dst_root, strip_all_spaces, logger, dir_manager)
        rel_src = md_path.relative_to(src_root)
        rel_dst = out_path.relative_to(dst_root)
        logger.info(f"{rel_src} -> {rel_dst}")
        processed_count += 1
    
    # 结束步骤
    logger.log_end(True, f"清理MD文件完成 - 处理了 {processed_count} 个文件")

if __name__ == "__main__":
    import argparse
    
    # 获取步骤配置
    step_config = get_step_config("06")
    
    # 初始化日志记录器
    logger = get_logger("06_clean_md")
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("06")
    
    parser = argparse.ArgumentParser(description="清理 Markdown 文件（删除空行、纯符号行、尾部空格，处理引用行，可选压缩空格）")
    parser.add_argument("--src", type=str, default=None, help="源 Markdown 文件目录")
    parser.add_argument("--dst", type=str, default=None, help="输出目录")
    parser.add_argument("--strip-all-spaces", action="store_true", help="压缩行内多个连续空格为一个")
    args = parser.parse_args()

    # 使用配置中的路径，如果命令行参数没有提供
    src_root = Path(args.src) if args.src else Path(step_config["input_dir"])
    dst_root = Path(args.dst) if args.dst else Path(step_config["output_dir"])
    
    if not src_root.exists():
        logger.error(f"源目录不存在: {src_root}")
        sys.exit(1)
    
    process_dir(src_root, dst_root, args.strip_all_spaces)