#!/usr/bin/env python3
"""
集中配置文件 - 邮件处理工作流程
定义所有共享配置项，包括目录路径、日志设置、处理参数等
"""

import os
from pathlib import Path
from datetime import datetime

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()

def get_project_root():
    """获取项目根目录"""
    return PROJECT_ROOT

# 基础目录配置
BASE_DIR = PROJECT_ROOT
LOG_DIR = BASE_DIR / "Logs"
DATA_DIR = BASE_DIR / "Data"

# 确保基础目录存在
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# 时间戳格式
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# 步骤配置
STEPS = {
    "01": {
        "name": "Email Classification",
        "script": "01_read_copy_by_To.py",
        "input_dir": DATA_DIR / "Email",
        "output_dir": DATA_DIR / "01_Classified",
        "log_prefix": "01_Email_Classification"
    },
    "02": {
        "name": "Conversation Thread Organization",
        "script": "02_ConversationIndex_uuid_modified.py",
        "input_dir": DATA_DIR / "01_Classified",
        "output_dir": DATA_DIR / "02_Conversation_Threads",
        "log_prefix": "02_Conversation_Threads"
    },
    "03": {
        "name": "Deduplication",
        "script": "03/main.py",
        "input_dir": DATA_DIR / "02_Conversation_Threads",
        "output_dir": DATA_DIR / "03_Deduplicated",
        "log_prefix": "03_Deduplication",
        "backup_dir": DATA_DIR / "03_Backup"
    },
    "04": {
        "name": "Format Conversion",
        "script": "04_msg_to_md.py",
        "input_dir": DATA_DIR / "03_Deduplicated",
        "output_dir": DATA_DIR / "04_Markdown_Files",
        "log_prefix": "04_Format_Conversion"
    },
    "05": {
        "name": "History Email Splitting",
        "script": "05_split_history.py",
        "input_dir": DATA_DIR / "04_Markdown_Files",
        "output_dir": DATA_DIR / "05_Split_History",
        "log_prefix": "05_History_Email_Splitting"
    },
    "06": {
        "name": "Content Cleaning",
        "script": "06_clean_md.py",
        "input_dir": DATA_DIR / "05_Split_History",
        "output_dir": DATA_DIR / "06_Cleaned",
        "log_prefix": "06_Content_Cleaning"
    },
    "07": {
        "name": "Intelligent Annotation",
        "script": "07/0702_process_all_markdown.py",
        "input_dir": DATA_DIR / "06_Cleaned",
        "output_dir": DATA_DIR / "07_Annotated",
        "log_prefix": "07_Intelligent_Annotation",
        "numbered_dir": DATA_DIR / "07_Numbered",
        "json_dir": DATA_DIR / "07_Json",
        "system_prompt": BASE_DIR / "07" / "system_prompt_mark.md"
    }
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "encoding": "utf-8"
}

# 邮件处理配置
EMAIL_CONFIG = {
    "extensions": [".msg"],
    "encoding_priority": ["utf-8", "utf-8-sig", "gb18030", "gbk", "gb2312", "cp1252", "latin1"],
    "max_workers": min(os.cpu_count() or 1, 6)
}

# AI处理配置
AI_CONFIG = {
    "provider": "siliconflow",  # 可选: siliconflow, azure
    "model": "default",
    "max_tokens": 4096,
    "temperature": 0.1
}

# 获取步骤配置
def get_step_config(step_id):
    """获取指定步骤的配置"""
    return STEPS.get(step_id, {})

# 获取步骤输入目录
def get_step_input_dir(step_id):
    """获取指定步骤的输入目录"""
    return get_step_config(step_id).get("input_dir")

# 获取步骤输出目录
def get_step_output_dir(step_id):
    """获取指定步骤的输出目录"""
    return get_step_config(step_id).get("output_dir")

# 获取步骤日志文件路径
def get_step_log_path(step_id, script_name=None):
    """获取指定步骤的日志文件路径"""
    step_config = get_step_config(step_id)
    log_prefix = step_config.get("log_prefix", f"{step_id}_处理")
    script_name = script_name or step_config.get("script", "unknown.py")
    
    # 提取脚本文件名（不含路径）
    script_name = Path(script_name).name
    
    # 创建日志文件名
    log_filename = f"{log_prefix}_{script_name}_{TIMESTAMP}.log"
    return LOG_DIR / log_filename

# 确保目录存在
def ensure_dir(dir_path):
    """确保目录存在，如果不存在则创建"""
    if isinstance(dir_path, str):
        dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

# 获取所有步骤的输入输出目录
def prepare_all_directories():
    """创建所有步骤需要的目录"""
    for step_id, config in STEPS.items():
        # 创建输入目录
        input_dir = config.get("input_dir")
        if input_dir:
            ensure_dir(input_dir)
        
        # 创建输出目录
        output_dir = config.get("output_dir")
        if output_dir:
            ensure_dir(output_dir)
        
        # 创建特殊目录（如备份目录等）
        if "backup_dir" in config:
            ensure_dir(config["backup_dir"])
        if "numbered_dir" in config:
            ensure_dir(config["numbered_dir"])
        if "json_dir" in config:
            ensure_dir(config["json_dir"])

# 初始化所有目录
if __name__ == "__main__":
    prepare_all_directories()
    print("所有目录已创建完成")
    print(f"日志目录: {LOG_DIR}")
    print(f"数据目录: {DATA_DIR}")