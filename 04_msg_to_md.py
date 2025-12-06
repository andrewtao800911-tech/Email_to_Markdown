#!/usr/bin/env python3
"""
msg_to_md.py

Convert .msg files to .md files, preserving relative paths.
- Subject -> Markdown H1
- Metadata -> bold lines (From, To, Cc, Date, Attachments, Source-File)
- Body -> plain text
- Attachments not saved, only names listed
- Logs success and failures
- Handles multiple encodings to avoid decode errors

Usage:
    python msg_to_md.py --src "Review/thread_classification" --dst "Review/thread_classification_md"
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

# 导入配置和日志管理模块
try:
    from config import get_step_config
    from logging_utils import get_logger
    from directory_manager import get_directory_manager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py、logging_utils.py和directory_manager.py文件在当前目录或Python路径中")
    sys.exit(1)

# 尝试的编码顺序
_TRY_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk", "gb2312", "cp1252", "latin1")


def try_decode_bytes(b: bytes) -> str:
    for enc in _TRY_ENCODINGS:
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("utf-8", errors="replace")


def safe_str(obj) -> str:
    if obj is None:
        return ""
    if isinstance(obj, (bytes, bytearray)):
        return try_decode_bytes(obj)
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def extract_attachment_names(msg) -> List[str]:
    names = []
    try:
        for att in getattr(msg, "attachments", []) or []:
            name = None
            for attr in ("longFilename", "shortFilename", "filename", "name"):
                try:
                    val = getattr(att, attr, None)
                except Exception:
                    val = None
                if val:
                    name = safe_str(val)
                    break
            if not name:
                name = "<unknown>"
            names.append(name)
    except Exception as e:
        # 使用全局logger而不是logging
        logger = get_logger("04_msg_to_md")
        logger.debug(f"读取附件错误: {e}")
    return names


def msg_to_text(msg) -> str:
    body = ""
    try:
        raw_body = getattr(msg, "body", None)
        if isinstance(raw_body, (bytes, bytearray)):
            body = try_decode_bytes(raw_body).strip()
        else:
            body = safe_str(raw_body).strip()
    except Exception as e:
        print(f"获取body失败: {e}")
        body = ""

    if not body:
        try:
            html = getattr(msg, "htmlBody", None)
            if html:
                import html2text
                if isinstance(html, (bytes, bytearray)):
                    html = try_decode_bytes(html)
                body = html2text.html2text(safe_str(html)).strip()
        except Exception as e:
            print(f"获取htmlBody失败: {e}")
            body = body or ""
            
    # 如果仍然没有正文，尝试获取RTF
    if not body:
        try:
            rtf = getattr(msg, "rtfBody", None)
            if rtf:
                # 尝试使用rtf2text库，如果没有则跳过
                try:
                    from striprtf.striprtf import rtf_to_text
                    if isinstance(rtf, (bytes, bytearray)):
                        rtf = try_decode_bytes(rtf)
                    body = rtf_to_text(rtf).strip()
                except ImportError:
                    print("未安装striprtf库，无法处理RTF格式")
                except Exception as e:
                    print(f"RTF转换失败: {e}")
        except Exception as e:
            print(f"获取rtfBody失败: {e}")
            
    return body or ""


def convert_one(msg_path: Path, src_root: Path, dst_root: Path) -> Path:
    import extract_msg

    # 尝试不同的编码方式
    encodings_to_try = ["utf-8", "gb18030", "gbk", "gb2312", "cp1252", "latin1"]
    
    msg = None
    last_error = None
    
    # 首先尝试不指定编码
    try:
        msg = extract_msg.Message(str(msg_path))
    except Exception as e:
        last_error = e
        
        # 如果失败，尝试不同的编码
        for enc in encodings_to_try:
            try:
                msg = extract_msg.Message(str(msg_path), overrideEncoding=enc)
                break
            except Exception as e2:
                last_error = e2
                continue
    
    if msg is None:
        raise Exception(f"无法使用任何编码读取MSG文件: {last_error}")

    # 安全地获取主题
    subj = ""
    try:
        subj = safe_str(getattr(msg, "subject", None)).strip()
    except Exception as e:
        print(f"获取主题失败: {e}")
        subj = msg_path.stem
    
    # 安全地获取其他字段
    sender = ""
    try:
        sender = safe_str(getattr(msg, "sender", None)).strip()
    except Exception as e:
        print(f"获取发件人失败: {e}")
        
    to = ""
    try:
        to = safe_str(getattr(msg, "to", None)).strip()
    except Exception as e:
        print(f"获取收件人失败: {e}")
        
    cc = ""
    try:
        cc = safe_str(getattr(msg, "cc", None)).strip()
    except Exception as e:
        print(f"获取抄送失败: {e}")
        
    date = ""
    try:
        date = safe_str(getattr(msg, "date", None)).strip()
    except Exception as e:
        print(f"获取日期失败: {e}")
        
    attachments = []
    try:
        attachments = extract_attachment_names(msg)
    except Exception as e:
        print(f"获取附件失败: {e}")
        
    body = ""
    try:
        body = msg_to_text(msg)
    except Exception as e:
        print(f"获取正文失败: {e}")
        body = f"(无法获取正文: {e})"

    try:
        rel = msg_path.relative_to(src_root)
    except Exception:
        rel = Path(msg_path.name)
    dst_path = dst_root / rel.with_suffix(".md")
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# {subj}\n")
    if sender:
        lines.append(f"**From: {sender}**")
    if to:
        lines.append(f"**To: {to}**")
    if cc:
        lines.append(f"**Cc: {cc}**")
    if date:
        lines.append(f"**Date: {date}**")
    if attachments:
        names = "; ".join(attachments)
        lines.append(f"**Attachments: {names}**")
    lines.append(f"**Source-File: {str(msg_path)}**\n")
    lines.append(body if body else "(No body text found)")

    content = "\n".join(lines).strip() + "\n"
    dst_path.write_text(content, encoding="utf-8", errors="replace")
    return dst_path


def walk_and_convert(src_root: Path, dst_root: Path, dry_run: bool = False) -> Tuple[int, int]:
    # 获取步骤配置
    step_config = get_step_config("04")
    
    # 初始化日志记录器
    logger = get_logger("04_msg_to_md")
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("04")
    
    # 创建失败记录文件
    failures_file = dst_root / "failures.txt"
    failures_file.write_text("", encoding="utf-8")

    converted, failed = 0, 0

    for path in src_root.rglob("*.msg"):
        try:
            if dry_run:
                logger.info(f"[DRY] 将转换: {path}")
            else:
                out = convert_one(path, src_root, dst_root)
                logger.info(f"[OK] {path} -> {out}")
            converted += 1
        except Exception as e:
            failed += 1
            reason = repr(e)
            logger.error(f"[ERR] {path} | {reason}")
            with open(failures_file, "a", encoding="utf-8") as fh:
                fh.write(f"{path}\t{reason}\n")

    return converted, failed


def main():
    # 获取步骤配置
    step_config = get_step_config("04")
    
    # 初始化日志记录器
    logger = get_logger("04_msg_to_md")
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("04")
    
    # 开始步骤
    logger.log_start()
    
    parser = argparse.ArgumentParser(description="Convert .msg files to .md preserving relative paths.")
    parser.add_argument("--src", type=str, default=None, help="Source folder to scan for .msg files (recursive).")
    parser.add_argument("--dst", type=str, default=None, help="Destination root to write .md files (preserve relative paths).")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files; just show what would be done.")
    args = parser.parse_args()

    # 使用配置中的路径，如果命令行参数没有提供
    src_root = Path(args.src) if args.src else Path("c:\\code\\PCG_Maxkb_review_202512\\data\\02_Conversation_Threads")
    dst_root = Path(args.dst) if args.dst else Path(step_config["output_dir"])

    if not src_root.exists():
        logger.error(f"源文件夹不存在: {src_root}")
        sys.exit(2)
    
    # 确保输出目录存在
    dir_manager.ensure_directory_exists(dst_root)

    converted, failed = walk_and_convert(src_root, dst_root, dry_run=args.dry_run)
    
    # 结束步骤
    logger.log_end(success=True, message=f"MSG转MD处理完成 - 成功: {converted}, 失败: {failed}")
    
    print(f"完成。成功转换: {converted}, 失败: {failed}")


if __name__ == "__main__":
    main()







