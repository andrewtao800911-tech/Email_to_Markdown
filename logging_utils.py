#!/usr/bin/env python3
"""
统一日志管理模块
提供统一的日志记录功能，所有步骤共享相同的日志格式和存储位置
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union

# 导入配置
try:
    from config import LOG_CONFIG, LOG_DIR, get_step_log_path
except ImportError:
    # 如果无法导入配置，使用默认值
    LOG_DIR = Path("Logs")
    LOG_DIR.mkdir(exist_ok=True)
    
    LOG_CONFIG = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "encoding": "utf-8"
    }
    
    def get_step_log_path(step_id, script_name=None):
        """备用函数，当无法导入config时使用"""
        script_name = script_name or "unknown.py"
        script_name = Path(script_name).name
        log_filename = f"{step_id}_{script_name}.log"
        return LOG_DIR / log_filename


class StepLogger:
    """步骤日志记录器类，封装日志记录功能"""
    
    def __init__(self, step_id: str, script_name: Optional[str] = None, 
                 logger_name: Optional[str] = None, 
                 console_output: bool = True):
        """
        初始化步骤日志记录器
        
        Args:
            step_id: 步骤ID (如 "01", "02" 等)
            script_name: 脚本名称 (如 "01_read_copy_by_To.py")
            logger_name: 日志记录器名称，默认使用步骤ID
            console_output: 是否同时输出到控制台
        """
        self.step_id = step_id
        self.script_name = script_name
        self.logger_name = logger_name or f"step_{step_id}"
        self.console_output = console_output
        
        # 获取日志文件路径
        self.log_file_path = get_step_log_path(step_id, script_name)
        
        # 确保日志目录存在
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建日志记录器
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(getattr(logging, LOG_CONFIG.get("level", "INFO")))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建文件处理器
            file_handler = logging.FileHandler(
                self.log_file_path, 
                encoding=LOG_CONFIG.get("encoding", "utf-8")
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 创建格式化器
            formatter = logging.Formatter(
                LOG_CONFIG.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                datefmt=LOG_CONFIG.get("date_format", "%Y-%m-%d %H:%M:%S")
            )
            file_handler.setFormatter(formatter)
            
            # 添加文件处理器
            self.logger.addHandler(file_handler)
            
            # 如果需要，添加控制台处理器
            if console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.INFO)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告信息"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """记录错误信息"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """记录严重错误信息"""
        self.logger.critical(message)
    
    def exception(self, message: str):
        """记录异常信息，包含堆栈跟踪"""
        self.logger.exception(message)
    
    def log_start(self):
        """记录步骤开始"""
        self.info(f"===== 步骤 {self.step_id} 开始 =====")
        if self.script_name:
            self.info(f"脚本: {self.script_name}")
        self.info(f"日志文件: {self.log_file_path}")
    
    def log_end(self, success: bool = True, message: str = ""):
        """记录步骤结束"""
        if success:
            self.info(f"===== 步骤 {self.step_id} 成功完成 =====")
        else:
            self.error(f"===== 步骤 {self.step_id} 失败 =====")
        
        if message:
            if success:
                self.info(message)
            else:
                self.error(message)
    
    def log_progress(self, current: int, total: int, item_name: str = "项目"):
        """记录进度信息"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.info(f"进度: {current}/{total} ({percentage:.1f}%) - {item_name}")
    
    def progress(self, message: str):
        """记录进度信息（简化版本）"""
        self.info(message)
    
    def log_file_operation(self, operation: str, src: Union[str, Path], 
                           dst: Optional[Union[str, Path]] = None, success: bool = True):
        """记录文件操作"""
        if success:
            if dst:
                self.info(f"{operation}: {src} -> {dst}")
            else:
                self.info(f"{operation}: {src}")
        else:
            if dst:
                self.error(f"{operation}失败: {src} -> {dst}")
            else:
                self.error(f"{operation}失败: {src}")


def get_logger(step_id: str, script_name: Optional[str] = None, 
               logger_name: Optional[str] = None, 
               console_output: bool = True) -> StepLogger:
    """
    获取步骤日志记录器
    
    Args:
        step_id: 步骤ID (如 "01", "02" 等)
        script_name: 脚本名称 (如 "01_read_copy_by_To.py")
        logger_name: 日志记录器名称，默认使用步骤ID
        console_output: 是否同时输出到控制台
    
    Returns:
        StepLogger: 步骤日志记录器实例
    """
    return StepLogger(step_id, script_name, logger_name, console_output)


def setup_basic_logging(log_level: str = "INFO"):
    """设置基本日志记录，用于没有步骤ID的简单脚本"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=LOG_CONFIG.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        datefmt=LOG_CONFIG.get("date_format", "%Y-%m-%d %H:%M:%S")
    )


# 示例用法
if __name__ == "__main__":
    # 创建一个测试日志记录器
    logger = get_logger("test", "test_script.py")
    
    # 记录步骤开始
    logger.log_start()
    
    # 记录不同级别的消息
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    # 记录文件操作
    logger.log_file_operation("复制", "source.txt", "destination.txt", True)
    logger.log_file_operation("删除", "old.txt", success=False)
    
    # 记录进度
    logger.log_progress(5, 10, "文件处理")
    
    # 记录步骤结束
    logger.log_end(True, "测试完成")