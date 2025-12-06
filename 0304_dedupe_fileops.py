#!/usr/bin/env python3
"""
邮件去重处理 - 文件操作工具
整合03目录中的fileops.py功能
"""

import sys
from pathlib import Path
import shutil
from datetime import datetime

# 导入配置和日志管理模块
try:
    from directory_manager import get_directory_manager
    import importlib.util
    
    # 动态导入以数字开头的模块
    spec = importlib.util.spec_from_file_location("dedupe_config", "0301_dedupe_config.py")
    dedupe_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dedupe_config)
    
    # 从模块中导入需要的函数
    get_dedupe_config = dedupe_config.get_dedupe_config
    get_dedupe_logger = dedupe_config.get_dedupe_logger
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保相关配置文件在当前目录或Python路径中")
    sys.exit(1)

def safe_move(src: Path, classified_root: Path = None):
    """
    安全移动文件，保留相对路径结构
    
    Args:
        src: 源文件路径
        classified_root: 分类邮件的根目录，默认为步骤配置中的backup_dir
        
    Returns:
        目标路径（如果移动成功）或None（如果出错）
    """
    # 获取步骤配置
    step_config = get_dedupe_config()
    
    # 初始化日志记录器
    logger = get_dedupe_logger("03_fileops")
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("03")
    
    if classified_root is None:
        classified_root = Path(step_config["backup_dir"])  # 使用配置中的备份目录
        
    try:
        # 计算相对于thread_classification目录的路径
        # 重复邮件目标目录需与"thread_classification"目录同级
        thread_classification_dir = Path(step_config["input_dir"])
        relative_path = src.relative_to(thread_classification_dir)
    except ValueError as e:
        logger.error(f"文件 {src} 不在thread分类目录 {thread_classification_dir} 下: {e}")
        return None

    # 构建目标路径，保持与源文件在"thread_classification"目录中的相对路径结构一致
    dest_path = classified_root / relative_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果是DRY_RUN模式，仅记录日志
    if step_config.get("dry_run", False):
        logger.info(f"[DRY RUN] 将移动: {src} -> {dest_path}")
        return dest_path

    # 处理目标文件已存在的情况
    if dest_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest_path = dest_path.with_stem(f"{dest_path.stem}_{timestamp}")

    # 执行文件移动
    try:
        shutil.move(str(src), str(dest_path))
        logger.info(f"已移动: {src} -> {dest_path}")
        logger.log_file_operation("move", str(src), str(dest_path))
        return dest_path
    except Exception as e:
        logger.error(f"移动失败 {src} -> {dest_path}: {e}")
        return None