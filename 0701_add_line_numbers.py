import os
import sys
from pathlib import Path

# 导入配置和日志管理模块
try:
    from config import get_step_config
    from logging_utils import get_logger
    from directory_manager import ensure_dir
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py、logging_utils.py和directory_manager.py文件在当前目录或Python路径中")
    sys.exit(1)

def read_file(file_path):
    """读取文件内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(file_path, content):
    """写入内容到文件"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def add_line_numbers(content):
    """给文本添加行号，格式：0001 | 内容"""
    lines = content.splitlines()
    numbered_lines = []
    # 使用 1-based 索引，与后续 LLM 的理解保持一致
    for i, line in enumerate(lines, 1):
        # {:04d} 表示数字不足4位补0，例如 1 -> 0001
        numbered_lines.append(f"{i:04d} | {line}")
    return "\n".join(numbered_lines)

def main():
    # 获取步骤配置和日志记录器
    step_config = get_step_config("07")
    logger = get_logger("07", "0701_add_line_numbers.py")
    
    # 记录处理开始
    logger.log_start()
    
    try:
        # 使用配置文件中的路径
        source_dir = step_config["input_dir"]
        target_dir = step_config["numbered_dir"]
        
        # 确保输出目录存在
        ensure_dir(target_dir)
        
        if not os.path.exists(source_dir):
            logger.error(f"源目录不存在: {source_dir}")
            logger.log_end(False, "源目录不存在")
            return

        files_processed = 0
        
        # 获取所有MD文件
        md_files = []
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
        
        logger.info(f"找到 {len(md_files)} 个MD文件，开始处理...")
        
        for i, md_file in enumerate(md_files, 1):
            try:
                # 计算相对路径，保持目录结构
                rel_path = os.path.relpath(md_file, source_dir)
                dst_path = os.path.join(target_dir, rel_path)
                
                logger.info(f"[{i}/{len(md_files)}] 正在处理: {rel_path}")
                
                # 读取 -> 加行号 -> 写入
                content = read_file(md_file)
                numbered_content = add_line_numbers(content)
                write_file(dst_path, numbered_content)
                
                files_processed += 1
                
            except Exception as e:
                logger.error(f"处理失败 {md_file}: {e}")

        logger.info(f"处理完成！共生成 {files_processed} 个带行号文件。")
        logger.log_end(True, f"成功生成 {files_processed} 个带行号文件，输出到 {target_dir}")
        
    except Exception as e:
        logger.log_end(False, f"处理过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()