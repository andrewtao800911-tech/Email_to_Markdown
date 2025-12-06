#!/usr/bin/env python3
"""
目录管理模块
统一管理邮件处理工作流程中的所有目录操作
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union

# 导入配置
try:
    from config import (
        STEPS, get_step_config, get_step_input_dir, 
        get_step_output_dir, ensure_dir, prepare_all_directories
    )
    from logging_utils import get_logger
except ImportError:
    # 如果无法导入配置，使用默认值
    STEPS = {}
    
    def get_step_config(step_id):
        return {}
    
    def get_step_input_dir(step_id):
        return None
    
    def get_step_output_dir(step_id):
        return None
    
    def ensure_dir(dir_path):
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def prepare_all_directories():
        pass
    
    class MockLogger:
        def info(self, msg): pass
        def error(self, msg): pass
        def debug(self, msg): pass
        def warning(self, msg): pass
    
    def get_logger(step_id, script_name=None):
        return MockLogger()


class DirectoryManager:
    """目录管理器类，封装目录操作功能"""
    
    def __init__(self, step_id: str, logger=None):
        """
        初始化目录管理器
        
        Args:
            step_id: 步骤ID (如 "01", "02" 等)
            logger: 日志记录器实例，如果为None则创建一个新的
        """
        self.step_id = step_id
        self.step_config = get_step_config(step_id)
        self.logger = logger or get_logger(step_id)
        
        # 获取输入输出目录
        self.input_dir = get_step_input_dir(step_id)
        self.output_dir = get_step_output_dir(step_id)
        
        # 确保目录存在
        if self.input_dir:
            ensure_dir(self.input_dir)
        if self.output_dir:
            ensure_dir(self.output_dir)
    
    def get_input_dir(self) -> Optional[Path]:
        """获取输入目录路径"""
        return self.input_dir
    
    def get_output_dir(self) -> Optional[Path]:
        """获取输出目录路径"""
        return self.output_dir
    
    def get_special_dir(self, dir_key: str) -> Optional[Path]:
        """
        获取特殊目录路径（如备份目录、编号目录等）
        
        Args:
            dir_key: 目录键名（如 "backup_dir", "numbered_dir" 等）
        
        Returns:
            目录路径，如果不存在则返回None
        """
        dir_path = self.step_config.get(dir_key)
        if dir_path:
            ensure_dir(dir_path)
            return dir_path
        return None
    
    def ensure_directory_exists(self, dir_path: Union[str, Path]):
        """
        确保目录存在，如果不存在则创建
        
        Args:
            dir_path: 目录路径
        """
        ensure_dir(dir_path)
        self.logger.debug(f"确保目录存在: {dir_path}")
    
    def ensure_all_dirs(self):
        """确保所有相关目录存在"""
        # 确保输入输出目录存在
        if self.input_dir:
            ensure_dir(self.input_dir)
            self.logger.debug(f"确保输入目录存在: {self.input_dir}")
        
        if self.output_dir:
            ensure_dir(self.output_dir)
            self.logger.debug(f"确保输出目录存在: {self.output_dir}")
        
        # 确保特殊目录存在
        for key, dir_path in self.step_config.items():
            if key.endswith("_dir") and dir_path:
                ensure_dir(dir_path)
                self.logger.debug(f"确保特殊目录存在: {key} -> {dir_path}")
    
    def list_files(self, pattern: str = "*", recursive: bool = True) -> List[Path]:
        """
        列出输入目录中的文件
        
        Args:
            pattern: 文件名模式（如 "*.msg"）
            recursive: 是否递归搜索子目录
        
        Returns:
            文件路径列表
        """
        if not self.input_dir or not self.input_dir.exists():
            self.logger.warning(f"输入目录不存在: {self.input_dir}")
            return []
        
        if recursive:
            files = list(self.input_dir.rglob(pattern))
        else:
            files = list(self.input_dir.glob(pattern))
        
        self.logger.info(f"在 {self.input_dir} 中找到 {len(files)} 个匹配 '{pattern}' 的文件")
        return files
    
    def get_files_by_extension(self, dir_path: Union[str, Path], extension: str, recursive: bool = False) -> List[Union[str, Path]]:
        """
        获取指定目录下指定扩展名的所有文件
        
        Args:
            dir_path: 目录路径
            extension: 文件扩展名（如 ".msg"）
            recursive: 是否递归搜索子目录
        
        Returns:
            文件路径列表（如果recursive为True则返回完整路径，否则返回文件名）
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            self.logger.warning(f"目录不存在: {dir_path}")
            return []
        
        # 确保扩展名以点开头
        if not extension.startswith('.'):
            extension = '.' + extension
        
        files = []
        if recursive:
            # 递归搜索，返回完整路径
            for file_path in dir_path.rglob(f"*{extension}"):
                if file_path.is_file():
                    files.append(file_path)
        else:
            # 只搜索当前目录，返回文件名
            for file_path in dir_path.glob(f"*{extension}"):
                if file_path.is_file():
                    files.append(file_path.name)
        
        self.logger.info(f"在 {dir_path} 中找到 {len(files)} 个 {extension} 文件")
        return files
    
    def get_subdirectories(self, dir_path: Union[str, Path]) -> List[Path]:
        """
        获取指定目录下的所有子目录
        
        Args:
            dir_path: 目录路径
        
        Returns:
            子目录路径列表
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            self.logger.warning(f"目录不存在: {dir_path}")
            return []
        
        subdirs = []
        for item in dir_path.iterdir():
            if item.is_dir():
                subdirs.append(item)
        
        self.logger.info(f"在 {dir_path} 中找到 {len(subdirs)} 个子目录")
        return subdirs
    
    def copy_file(self, src: Union[str, Path], dst_name: Optional[str] = None, 
                  dst_subdir: Optional[str] = None) -> Path:
        """
        复制文件到输出目录
        
        Args:
            src: 源文件路径
            dst_name: 目标文件名，如果为None则使用源文件名
            dst_subdir: 目标子目录（相对于输出目录）
        
        Returns:
            目标文件路径
        """
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src_path}")
        
        # 确定目标路径
        dst_name = dst_name or src_path.name
        if dst_subdir:
            dst_dir = self.output_dir / dst_subdir
            ensure_dir(dst_dir)
        else:
            dst_dir = self.output_dir
        
        dst_path = dst_dir / dst_name
        
        # 复制文件
        try:
            shutil.copy2(src_path, dst_path)
            self.logger.info(f"文件复制成功: {src_path} -> {dst_path}")
            return dst_path
        except Exception as e:
            self.logger.error(f"文件复制失败: {src_path} -> {dst_path}, 错误: {str(e)}")
            raise
    
    def move_file(self, src: Union[str, Path], dst_name: Optional[str] = None, 
                  dst_subdir: Optional[str] = None) -> Path:
        """
        移动文件到输出目录
        
        Args:
            src: 源文件路径
            dst_name: 目标文件名，如果为None则使用源文件名
            dst_subdir: 目标子目录（相对于输出目录）
        
        Returns:
            目标文件路径
        """
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src_path}")
        
        # 确定目标路径
        dst_name = dst_name or src_path.name
        if dst_subdir:
            dst_dir = self.output_dir / dst_subdir
            ensure_dir(dst_dir)
        else:
            dst_dir = self.output_dir
        
        dst_path = dst_dir / dst_name
        
        # 移动文件
        try:
            shutil.move(src_path, dst_path)
            self.logger.info(f"文件移动成功: {src_path} -> {dst_path}")
            return dst_path
        except Exception as e:
            self.logger.error(f"文件移动失败: {src_path} -> {dst_path}, 错误: {str(e)}")
            raise
    
    def create_subdir(self, subdir_name: str) -> Path:
        """
        在输出目录下创建子目录
        
        Args:
            subdir_name: 子目录名称
        
        Returns:
            子目录路径
        """
        subdir_path = self.output_dir / subdir_name
        ensure_dir(subdir_path)
        self.logger.info(f"创建子目录: {subdir_path}")
        return subdir_path
    
    def clean_output_dir(self, keep_structure: bool = False):
        """
        清理输出目录
        
        Args:
            keep_structure: 是否保持目录结构（只删除文件，保留目录）
        """
        if not self.output_dir or not self.output_dir.exists():
            self.logger.warning(f"输出目录不存在，无需清理: {self.output_dir}")
            return
        
        try:
            if keep_structure:
                # 只删除文件，保留目录结构
                for item in self.output_dir.rglob("*"):
                    if item.is_file():
                        item.unlink()
                        self.logger.debug(f"删除文件: {item}")
            else:
                # 删除整个目录内容
                shutil.rmtree(self.output_dir)
                ensure_dir(self.output_dir)
                self.logger.info(f"清理输出目录: {self.output_dir}")
            
            self.logger.info(f"输出目录清理完成: {self.output_dir}")
        except Exception as e:
            self.logger.error(f"清理输出目录失败: {self.output_dir}, 错误: {str(e)}")
            raise
    
    def get_dir_stats(self) -> dict:
        """
        获取目录统计信息
        
        Returns:
            包含文件数量、目录数量、总大小等信息的字典
        """
        stats = {
            "input_dir": str(self.input_dir) if self.input_dir else None,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "input_files": 0,
            "input_dirs": 0,
            "input_size": 0,
            "output_files": 0,
            "output_dirs": 0,
            "output_size": 0
        }
        
        # 统计输入目录
        if self.input_dir and self.input_dir.exists():
            for item in self.input_dir.rglob("*"):
                if item.is_file():
                    stats["input_files"] += 1
                    stats["input_size"] += item.stat().st_size
                elif item.is_dir():
                    stats["input_dirs"] += 1
        
        # 统计输出目录
        if self.output_dir and self.output_dir.exists():
            for item in self.output_dir.rglob("*"):
                if item.is_file():
                    stats["output_files"] += 1
                    stats["output_size"] += item.stat().st_size
                elif item.is_dir():
                    stats["output_dirs"] += 1
        
        return stats


def get_directory_manager(step_id: str, logger=None) -> DirectoryManager:
    """
    获取目录管理器实例
    
    Args:
        step_id: 步骤ID (如 "01", "02" 等)
        logger: 日志记录器实例，如果为None则创建一个新的
    
    Returns:
        DirectoryManager: 目录管理器实例
    """
    return DirectoryManager(step_id, logger)


def prepare_step_directories(step_id: str) -> dict:
    """
    准备指定步骤的所有目录
    
    Args:
        step_id: 步骤ID
    
    Returns:
        包含所有目录路径的字典
    """
    dir_manager = get_directory_manager(step_id)
    dir_manager.ensure_all_dirs()
    
    dirs = {
        "input_dir": dir_manager.get_input_dir(),
        "output_dir": dir_manager.get_output_dir()
    }
    
    # 添加特殊目录
    for key, dir_path in dir_manager.step_config.items():
        if key.endswith("_dir") and dir_path:
            dirs[key] = dir_path
    
    return dirs


# 示例用法
if __name__ == "__main__":
    # 准备所有步骤的目录
    prepare_all_directories()
    
    # 测试目录管理器
    step_id = "01"
    dir_manager = get_directory_manager(step_id)
    
    # 确保所有目录存在
    dir_manager.ensure_all_dirs()
    
    # 获取目录统计信息
    stats = dir_manager.get_dir_stats()
    print(f"目录统计信息: {stats}")
    
    # 列出输入目录中的所有文件
    files = dir_manager.list_files("*.msg")
    print(f"找到 {len(files)} 个.msg文件")