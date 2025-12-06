#!/usr/bin/env python3
"""
邮件去重处理 - 配置模块
整合03目录中的config.py和logging_setup.py功能
"""

from pathlib import Path
from datetime import datetime
from typing import Final
import logging
import sys
import multiprocessing

# 导入主配置
try:
    from config import get_step_config, get_project_root
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py文件在当前目录或Python路径中")
    sys.exit(1)

# 获取项目根目录
PROJECT_ROOT = get_project_root()

# 时间戳
TIMESTAMP: Final[str] = datetime.now().strftime('%Y%m%d_%H%M%S')

# 获取步骤配置
def get_dedupe_config():
    """获取去重处理的配置"""
    step_config = get_step_config("03")
    
    # 添加去重特定的配置
    dedupe_config = {
        "threshold": 0.94,      # 模糊匹配阈值
        "exact_only": False,     # 是否仅使用精确匹配
        "dry_run": False,        # 是否为试运行模式
        "debug": True,           # 调试模式
        "max_workers": min(6, (multiprocessing.cpu_count() or 1))  # 最大工作进程数
    }
    
    # 合并配置
    return {**step_config, **dedupe_config}

# 获取日志记录器
def get_dedupe_logger(logger_name: str = "03_dedupe"):
    """
    获取去重处理的日志记录器
    
    Args:
        logger_name: 日志记录器名称
        
    Returns:
        配置好的logger实例
    """
    try:
        from logging_utils import get_logger
        return get_logger("03", "0303_dedupe_main.py", logger_name)
    except ImportError:
        # 备用日志记录器
        logger = logging.getLogger(logger_name)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
            
        level = logging.DEBUG if get_dedupe_config().get("debug", False) else logging.INFO
        logger.setLevel(level)
        
        ch = logging.StreamHandler()
        ch.setLevel(level)
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(fmt)
        ch.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.propagate = False  # 避免重复日志
        
        return logger