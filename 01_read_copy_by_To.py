import extract_msg
import os
import shutil
import re
import argparse
from datetime import datetime
from collections import defaultdict
import sys

# 导入配置和日志管理模块
try:
    from config import get_step_config
    from logging_utils import get_logger
    from directory_manager import get_directory_manager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保config.py、logging_utils.py和directory_manager.py文件在当前目录或Python路径中")
    sys.exit(1)

# 简化版邮件分类脚本，专注于基本功能的稳定运行

def extract_email_domains(recipients):
    """
    从收件人信息中提取邮箱域名
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, recipients)
    domains = set()

    if emails:
        for email in emails:
            # 移除了冗余的 '@' 检查，因为正则表达式已经确保了邮箱格式
            domain = email.split('@')[1]
            domains.add(domain)
    else:
        # 如果没有找到有效邮箱，放入'unknown'文件夹
        domains.add('unknown')

    return domains

def process_email_file(msg, filename, classified_folder, logger, dir_manager):
    """
    处理单个邮件文件（优化版本，避免重复解析）
    """
    try:
        # 提取收件人信息
        recipients = msg.to or ""
        
        # 提取邮箱域名
        domains = extract_email_domains(recipients)
        
        # 记录日志
        logger.info(f"处理文件: {filename}")
        logger.debug(f"收件人信息: {recipients}")
        logger.debug(f"提取域名: {', '.join(domains)}")

        # 为每个域名创建文件夹并复制邮件
        for domain in domains:
            domain_folder = os.path.join(classified_folder, domain)
            dir_manager.ensure_directory_exists(domain_folder)

            # 复制邮件到域名文件夹
            dest_path = os.path.join(domain_folder, filename)
            try:
                # 获取原始文件路径
                msg_path = msg.filename
                shutil.copy2(msg_path, dest_path)
                logger.info(f"已复制 {filename} 到 {domain} 文件夹")
                logger.log_file_operation("copy", msg_path, dest_path)
            except PermissionError:
                logger.error(f"权限不足，无法复制文件 {filename} 到 {domain} 文件夹")
            except FileNotFoundError:
                logger.error(f"文件 {filename} 不存在")
            except Exception as e:
                logger.error(f"复制文件 {filename} 到 {domain} 文件夹时出错: {str(e)}")

    except Exception as e:
        logger.error(f"处理文件 {filename} 时出错: {str(e)}")

def main():
    """
    主函数，处理目录下所有.msg文件
    """
    # 获取步骤配置
    step_config = get_step_config("01")
    
    # 初始化日志记录器
    logger = get_logger("01_read_copy_by_To")
    logger.log_start()
    
    # 初始化目录管理器
    dir_manager = get_directory_manager("01")
    
    # 准备输入输出目录
    input_dir = step_config["input_dir"]
    output_dir = step_config["output_dir"]
    
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    
    # 确保输出目录存在
    dir_manager.ensure_directory_exists(output_dir)
    
    # 获取所有.msg文件
    msg_files = dir_manager.get_files_by_extension(input_dir, ".msg")
    total_files = len(msg_files)
    
    # 初始化统计信息
    success_count = 0
    error_count = 0
    domain_stats = defaultdict(int)
    
    logger.info(f"找到 {total_files} 个邮件文件待处理")
    
    try:
        # 遍历并处理所有.msg文件
        for i, filename in enumerate(msg_files):
            # 显示进度
            progress = (i + 1) / total_files * 100
            logger.progress(f"处理进度: {i+1}/{total_files} ({progress:.1f}%)")
            
            msg_path = os.path.join(input_dir, filename)
            
            try:
                # 读取邮件获取域名信息用于统计
                msg = extract_msg.Message(msg_path)
                recipients = msg.to or ""
                domains = extract_email_domains(recipients)
                
                # 更新域名统计
                for domain in domains:
                    domain_stats[domain] += 1
                
                # 处理邮件文件（传递已解析的msg对象，避免重复解析）
                process_email_file(msg, filename, output_dir, logger, dir_manager)
                success_count += 1
                
            except Exception as e:
                logger.error(f"处理文件 {filename} 时发生错误: {str(e)}")
                error_count += 1
        
        # 写入统计摘要
        logger.info("===== 处理摘要 =====")
        logger.info(f"总文件数: {total_files}")
        logger.info(f"成功处理: {success_count}")
        logger.info(f"处理失败: {error_count}")
        
        logger.info("域名分布统计:")
        for domain, count in sorted(domain_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"- {domain}: {count} 个文件")
        
        # 结束步骤
        logger.log_end(True, f"邮件分类处理完成 - 成功: {success_count}, 失败: {error_count}")
        
    except Exception as e:
        logger.error(f"处理过程中发生严重错误: {str(e)}")
        logger.log_end(False, "邮件分类处理中断")
        raise

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='按域名分类.msg邮件文件')
    parser.add_argument('-i', '--input', 
                      help='输入目录路径（可选，默认使用配置文件中的路径）')
    parser.add_argument('-o', '--output', 
                      help='输出目录路径（可选，默认使用配置文件中的路径）')
    
    args = parser.parse_args()
    
    # 如果提供了命令行参数，临时更新配置
    if args.input or args.output:
        try:
            from config import get_step_config
            step_config = get_step_config("01")
            
            if args.input:
                step_config["input_dir"] = args.input
            if args.output:
                step_config["output_dir"] = args.output
        except ImportError:
            print("警告: 无法导入配置文件，命令行参数将被忽略")
    
    # 调用主函数
    main()