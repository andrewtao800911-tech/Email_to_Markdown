#!/usr/bin/env python3
"""
split_history_md.py

识别并分割 Markdown 邮件文件中的历史邮件片段，使用分隔符在同一文件中标记历史邮件。
- 原始邮件主体保持不变
- 历史邮件使用 "======历史邮件======" 分隔符标记
- 历史邮件的邮件头（From: ... 到 Subject: ...）强制全部加粗，即使中间有空行
- 输出目录保持和源目录相同的层级结构

用法示例:
    python 05_split_history.py --src data/04_Markdown_Files --dst data/05_Split_History
"""

import re
import sys
from pathlib import Path

# 导入配置和日志管理模块
try:
    from config import get_step_config
    from logging_utils import get_logger
    from directory_manager import get_directory_manager, ensure_dir
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py、logging_utils.py和directory_manager.py文件在当前目录或Python路径中")
    sys.exit(1)

# 匹配历史邮件的起始行（多语言 From）
HISTORY_EMAIL_PATTERN = re.compile(
    r"^\s*(From\s*:|发件人\s*:|发信人\s*:|差出人\s*:|寄件者\s*:|Sender\s*:).*?@.*?$",
    re.IGNORECASE | re.MULTILINE
)

# 匹配邮件头字段（用于识别同一封邮件中的多个邮件头）
EMAIL_HEADER_PATTERN = re.compile(
    r"^\s*(From\s*:|发件人\s*:|发信人\s*:|差出人\s*:|寄件者\s*:|Sender\s*:|"
    r"To\s*:|收件人\s*:|宛先\s*:|Cc\s*:|抄送\s*:|Subject\s*:|件名\s*:|主题\s*:|Date\s*:|Sent\s*:|发送时间\s*:)",
    re.IGNORECASE
)

# 匹配头部字段（多语言 From/To/Cc/Subject/Date/Sent）
HEADER_FIELD_PATTERN = re.compile(
    r"^\s*(From\s*:|发件人\s*:|发信人\s*:|差出人\s*:|寄件者\s*:|Sender\s*:|"
    r"To\s*:|收件人\s*:|宛先\s*:|Cc\s*:|抄送\s*:|Subject\s*:|件名\s*:|主题\s*:|Date\s*:|Sent\s*:)",
    re.IGNORECASE
)

# 历史邮件分隔符
HISTORY_SEPARATOR = "\n\n======历史邮件======\n\n"

def process_history_emails(md_path: Path, src_root: Path, dst_root: Path):
    text = md_path.read_text(encoding="utf-8", errors="replace")
    matches = list(HISTORY_EMAIL_PATTERN.finditer(text))

    # 计算相对路径（去掉源根目录），保持目录层级
    rel_path = md_path.relative_to(src_root)
    out_dir = dst_root / rel_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 输出文件路径
    out_path = out_dir / rel_path.name

    # 如果没有找到历史邮件，直接复制原文件
    if not matches:
        out_path.write_text(text, encoding="utf-8")
        return out_path

    # ========== 构建新的邮件内容 ==========
    new_content = []
    
    # 添加原始邮件主体（去掉历史邮件部分）
    main_text = text[:matches[0].start()].rstrip()
    new_content.append(main_text)
    
    # ========== 处理历史邮件 ==========
    for i in range(len(matches)):
        # 确定当前邮件的起始位置
        start = matches[i].start()
        # 确定当前邮件的结束位置（下一个邮件的开始或文本结尾）
        if i < len(matches) - 1:
            # 如果不是最后一个邮件，结束位置是下一个邮件的开始
            end = matches[i + 1].start()
        else:
            # 如果是最后一个邮件，结束位置是文本结尾
            end = len(text)

        # 添加历史邮件分隔符
        new_content.append(HISTORY_SEPARATOR)
        
        # 提取当前邮件的完整内容
        email_content = text[start:end].strip()
        lines = email_content.splitlines()
        
        # 初始化邮件头和正文
        headers = []
        body = []
        in_headers = True
        
        # 处理邮件内容，分离邮件头和正文
        subject_found = False
        for line in lines:
            # 检查是否是邮件头字段
            if re.match(r"^\s*(From\s*:|发件人\s*:|发信人\s*:|差出人\s*:|寄件者\s*:|Sender\s*:|" +
                       r"To\s*:|收件人\s*:|宛先\s*:|Cc\s*:|抄送\s*:|Subject\s*:|件名\s*:|主题\s*:|" +
                       r"Date\s*:|Sent\s*:|发送时间\s*:)", line, re.IGNORECASE):
                in_headers = True
                headers.append(f"**{line.strip()}**")
                # 如果是主题行，标记为已找到
                if re.match(r"^\s*(Subject\s*:|件名\s*:|主题\s*:)", line, re.IGNORECASE):
                    subject_found = True
            else:
                # 如果是空行且还在处理邮件头，继续当作邮件头的一部分
                if in_headers and not line.strip():
                    headers.append(f"**{line.strip()}**")
                # 如果已经找到主题行，且当前行不是邮件头字段，且不是空白行，则认为正文开始
                elif subject_found and line.strip() and not re.match(r"^\s*(From\s*:|发件人\s*:|" +
                                                                    r"To\s*:|收件人\s*:|Cc\s*:|" +
                                                                    r"Date\s*:|Sent\s*:)", 
                                                                    line, re.IGNORECASE):
                    in_headers = False
                    body.append(line)
                elif not in_headers:
                    body.append(line)
                else:
                    # 其他情况继续当作邮件头处理
                    headers.append(f"**{line.strip()}**")
        
        # 提取 Subject
        subject_line = next((h for h in headers if any(keyword in h.lower() for keyword in ["subject:", "件名:", "主题:"])), None)
        if subject_line:
            # 移除加粗标记并提取主题文本
            subject_text = subject_line.strip("* ")
            # 移除主题关键字
            for keyword in ["subject:", "件名:", "主题:"]:
                if keyword in subject_text.lower():
                    subject = subject_text[subject_text.lower().find(keyword) + len(keyword):].strip()
                    break
            else:
                subject = subject_text.strip()
        else:
            subject = f"历史邮件{i+1}"
        
        # 添加历史邮件标题
        new_content.append(f"## {subject}\n")
        
        # 添加邮件头
        new_content.extend(headers)
        
        # 添加正文（如果有）
        if body:
            new_content.append("")
            new_content.extend(body)
    
    # 保存处理后的文件
    out_path.write_text("\n".join(new_content), encoding="utf-8")
    return out_path

def process_dir(src_dir: Path, dst_dir: Path):
    # 获取步骤配置和日志记录器
    step_config = get_step_config("05")
    logger = get_logger("05_split_history")
    dir_manager = get_directory_manager("05")
    
    # 记录处理开始
    logger.log_start()
    
    try:
        # 确保输出目录存在
        ensure_dir(dst_dir)
        
        # 获取所有MD文件
        md_files = list(src_dir.rglob("*.md"))
        total_files = len(md_files)
        
        logger.info(f"开始处理 {total_files} 个MD文件")
        
        # 处理每个MD文件
        for i, md_path in enumerate(md_files, 1):
            try:
                result_path = process_history_emails(md_path, src_dir, dst_dir)
                logger.info(f"[{i}/{total_files}] {md_path.relative_to(src_dir)} -> {result_path.relative_to(dst_dir)}")
            except Exception as e:
                logger.error(f"处理文件 {md_path.relative_to(src_dir)} 时出错: {str(e)}")
        
        # 记录处理完成
        logger.log_end(True, f"成功处理所有MD文件，输出到 {dst_dir}")
    except Exception as e:
        logger.log_end(False, f"处理过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="分割 Markdown 文件中的历史邮件片段")
    parser.add_argument("--src", type=str, help="源 Markdown 文件目录")
    parser.add_argument("--dst", type=str, help="输出目录")
    args = parser.parse_args()
    
    # 获取步骤配置
    step_config = get_step_config("05")
    
    # 使用命令行参数或配置文件中的默认路径
    src_dir = Path(args.src) if args.src else step_config["input_dir"]
    dst_dir = Path(args.dst) if args.dst else step_config["output_dir"]
    
    process_dir(src_dir, dst_dir)