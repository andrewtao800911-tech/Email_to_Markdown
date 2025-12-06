import extract_msg
import os
import re
import shutil
import base64
import uuid
import olefile
from collections import defaultdict
from datetime import datetime
import logging
from email.utils import parsedate_to_datetime

# 导入配置和日志管理模块
try:
    from config import get_step_config
    from logging_utils import get_logger
    from directory_manager import get_directory_manager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py、logging_utils.py和directory_manager.py文件在当前目录或Python路径中")
    exit(1)

# 设置extract_msg库的日志级别为WARNING，抑制INFO级别的消息
logging.getLogger('extract_msg').setLevel(logging.WARNING)


def find_all_msg_files(directory, dir_manager):
    """递归查找目录中的所有msg文件"""
    return dir_manager.get_files_by_extension(directory, ".msg", recursive=True)


def extract_guid_from_index(conversation_index, logger):
    """从ConversationIndex中提取GUID"""
    try:
        # ConversationIndex通常是base64编码的二进制数据
        if isinstance(conversation_index, str):
            # 解码base64
            binary_data = base64.b64decode(conversation_index)
            # 提取GUID部分（通常是前16字节）
            if len(binary_data) >= 16:
                guid_bytes = binary_data[:16]
                return str(uuid.UUID(bytes_le=guid_bytes))
        return None
    except Exception as e:
        logger.warning(f"提取GUID失败: {e}")
        return None


def normalize_subject(subject):
    """标准化邮件主题"""
    if not subject:
        return ""
    # 移除常见的回复前缀
    subject = re.sub(r'^(RE|FW|FWD|回复|转发)[:\s\[\]]+', '', subject, flags=re.IGNORECASE)
    # 移除多余空格
    subject = re.sub(r'\s+', ' ', subject).strip()
    return subject


def parse_all_msg_files(msg_files, logger):
    """解析所有msg文件，提取会话信息"""
    emails_by_thread = defaultdict(list)
    
    for msg_file in msg_files:
        try:
            msg = extract_msg.Message(msg_file)
            
            # 提取会话信息
            conversation_index = getattr(msg, 'conversationIndex', None)
            conversation_topic = getattr(msg, 'conversationTopic', None)
            
            # 如果没有conversationIndex，尝试使用其他标识符
            thread_id = None
            if conversation_index:
                thread_id = extract_guid_from_index(conversation_index, logger)
            
            # 如果无法从conversationIndex提取GUID，使用conversationTopic作为备用
            if not thread_id and conversation_topic:
                thread_id = conversation_topic
            
            # 如果还是没有thread_id，使用标准化的主题
            if not thread_id:
                subject = getattr(msg, 'subject', '')
                thread_id = normalize_subject(subject)
            
            # 收集邮件信息
            email_info = {
                'file_path': msg_file,
                'subject': getattr(msg, 'subject', ''),
                'sender': getattr(msg, 'sender', ''),
                'date': getattr(msg, 'date', None),
                'conversation_index': conversation_index,
                'conversation_topic': conversation_topic,
                'thread_id': thread_id
            }
            
            emails_by_thread[thread_id].append(email_info)
            msg.close()
            
        except Exception as e:
            logger.error(f"解析文件 {msg_file} 失败: {e}")
    
    return emails_by_thread


def classify_emails_by_thread(emails_by_thread, output_base_dir, logger, dir_manager):
    """按会话线程分类邮件"""
    thread_count = 0
    
    for thread_id, emails in emails_by_thread.items():
        # 按日期排序邮件，处理时区问题
        def get_sortable_date(email_date):
            if email_date is None:
                return datetime.min
            # 如果日期有时区信息，转换为无时区信息
            if hasattr(email_date, 'tzinfo') and email_date.tzinfo is not None:
                return email_date.replace(tzinfo=None)
            return email_date
        
        emails.sort(key=lambda x: get_sortable_date(x['date']))
        
        # 只有当会话包含多个邮件时才创建线程目录
        if len(emails) > 1:
            # 创建线程目录
            thread_dir = os.path.join(output_base_dir, f"thread_{thread_count:04d}")
            dir_manager.ensure_directory_exists(thread_dir)
            
            # 复制邮件文件
            for i, email_info in enumerate(emails):
                src_path = email_info['file_path']
                filename = os.path.basename(src_path)
                dest_path = os.path.join(thread_dir, f"{i:03d}_{filename}")
                
                try:
                    shutil.copy2(src_path, dest_path)
                    logger.info(f"已复制: {src_path} -> {dest_path}")
                    logger.log_file_operation("copy", src_path, dest_path)
                except Exception as e:
                    logger.error(f"复制失败 {src_path}: {e}")
        else:
            # 对于单个邮件的会话，直接复制到输出目录
            email_info = emails[0]
            src_path = email_info['file_path']
            filename = os.path.basename(src_path)
            dest_path = os.path.join(output_base_dir, filename)
            
            try:
                shutil.copy2(src_path, dest_path)
                logger.info(f"已复制单个邮件: {src_path} -> {dest_path}")
                logger.log_file_operation("copy", src_path, dest_path)
            except Exception as e:
                logger.error(f"复制失败 {src_path}: {e}")
        
        thread_count += 1
    
    return thread_count


def generate_report(emails_by_thread, output_dir, logger, dir_manager):
    """生成分类报告"""
    report_path = os.path.join(output_dir, "classification_report.txt")
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("邮件会话分类报告\n")
            f.write("=" * 50 + "\n\n")
            
            thread_count = 0
            for thread_id, emails in emails_by_thread.items():
                f.write(f"会话 {thread_count:04d}:\n")
                f.write(f"线程ID: {thread_id}\n")
                f.write(f"邮件数量: {len(emails)}\n")
                
                # 按日期排序，处理时区问题
                def get_sortable_date(email_date):
                    if email_date is None:
                        return datetime.min
                    # 如果日期有时区信息，转换为无时区信息
                    if hasattr(email_date, 'tzinfo') and email_date.tzinfo is not None:
                        return email_date.replace(tzinfo=None)
                    return email_date
                
                emails.sort(key=lambda x: get_sortable_date(x['date']))
                
                f.write("邮件列表:\n")
                for i, email in enumerate(emails):
                    date_str = email['date'].strftime('%Y-%m-%d %H:%M:%S') if email['date'] else '未知日期'
                    f.write(f"  {i:02d}. {date_str} - {email['sender']} - {email['subject']}\n")
                
                f.write("\n" + "-" * 50 + "\n\n")
                thread_count += 1
            
            f.write(f"总计会话数: {thread_count}\n")
            f.write(f"总计邮件数: {sum(len(emails) for emails in emails_by_thread.values())}\n")
        
        logger.info(f"报告已生成: {report_path}")
        logger.log_file_operation("create", None, report_path)
    except Exception as e:
        logger.error(f"生成报告失败: {e}")


def process_all_subdirectories(main_directory, output_base_dir, logger, dir_manager):
    """处理主目录下的所有子目录"""
    # 获取步骤配置
    step_config = get_step_config("01")
    classified_emails_dir = step_config["output_dir"]
    
    if not os.path.exists(classified_emails_dir):
        logger.error(f"目录不存在: {classified_emails_dir}")
        return
    
    # 获取classified_emails目录下的所有子目录
    subdirectories = dir_manager.get_subdirectories(classified_emails_dir)
    
    if not subdirectories:
        logger.warning(f"在 {classified_emails_dir} 中没有找到子目录")
        return
    
    total_threads = 0
    total_emails = 0
    
    for subdir in subdirectories:
        logger.info(f"处理子目录: {subdir}")
        
        # 查找所有msg文件
        msg_files = find_all_msg_files(subdir, dir_manager)
        logger.info(f"找到 {len(msg_files)} 个msg文件")
        
        if not msg_files:
            continue
        
        # 解析邮件文件
        emails_by_thread = parse_all_msg_files(msg_files, logger)
        
        # 创建输出目录
        subdir_name = os.path.basename(subdir)
        output_dir = os.path.join(output_base_dir, subdir_name)
        dir_manager.ensure_directory_exists(output_dir)
        
        # 分类邮件
        thread_count = classify_emails_by_thread(emails_by_thread, output_dir, logger, dir_manager)
        
        # 生成报告
        generate_report(emails_by_thread, output_dir, logger, dir_manager)
        
        total_threads += thread_count
        total_emails += len(msg_files)
        
        logger.info(f"完成处理 {subdir_name}: {thread_count} 个会话, {len(msg_files)} 封邮件")
    
    logger.info(f"所有子目录处理完成: 总计 {total_threads} 个会话, {total_emails} 封邮件")


def main():
    """主函数"""
    # 获取步骤配置
    step_config = get_step_config("02")
    
    # 初始化日志记录器
    logger = get_logger("02_ConversationIndex_uuid_modified")
    logger.log_start()
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("02")
    
    # 准备输入输出目录
    input_dir = step_config["input_dir"]
    output_dir = step_config["output_dir"]
    
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    
    # 确保输出目录存在
    dir_manager.ensure_directory_exists(output_dir)
    
    try:
        # 处理所有子目录
        process_all_subdirectories(input_dir, output_dir, logger, dir_manager)
        
        # 结束步骤
        logger.log_end(True, "邮件会话分类处理完成")
        
    except Exception as e:
        logger.error(f"处理过程中发生严重错误: {str(e)}")
        logger.log_end(False, "邮件会话分类处理中断")
        raise


if __name__ == "__main__":
    main()