#!/usr/bin/env python3
"""
邮件去重处理 - 主程序
整合03目录中的main.py和dedupe.py功能
"""

import sys
import os
import json
import argparse
import multiprocessing
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 导入配置和日志管理模块
try:
    from directory_manager import get_directory_manager
    import importlib.util
    
    # 动态导入以数字开头的模块
    spec1 = importlib.util.spec_from_file_location("dedupe_config", "0301_dedupe_config.py")
    dedupe_config = importlib.util.module_from_spec(spec1)
    spec1.loader.exec_module(dedupe_config)
    
    spec2 = importlib.util.spec_from_file_location("dedupe_utils", "0302_dedupe_utils.py")
    dedupe_utils = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(dedupe_utils)
    
    spec3 = importlib.util.spec_from_file_location("dedupe_fileops", "0304_dedupe_fileops.py")
    dedupe_fileops = importlib.util.module_from_spec(spec3)
    spec3.loader.exec_module(dedupe_fileops)
    
    # 从模块中导入需要的函数
    get_dedupe_config = dedupe_config.get_dedupe_config
    get_dedupe_logger = dedupe_config.get_dedupe_logger
    clean_body_text = dedupe_utils.clean_body
    exact_substring_match = dedupe_utils.is_exact_substring
    tokenized_contiguous_match = dedupe_utils.is_token_contiguous_subsequence
    fuzzy_similarity_match = dedupe_utils.is_fuzzy_similar
    safe_move = dedupe_fileops.safe_move
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保相关配置文件在当前目录或Python路径中")
    sys.exit(1)

def process_thread_dir(thread_dir: Path) -> Tuple[int, int, int, Dict[str, int]]:
    """
    处理单个thread_*目录中的邮件去重
    """
    # 获取步骤配置
    step_config = get_dedupe_config()
    logger = get_dedupe_logger("03_process")
    
    total_files = 0
    moved_files = 0
    skipped_files = 0
    domain_counts = {}
    
    # 获取子目录中的所有.msg文件
    msg_files = list(thread_dir.glob("*.msg"))
    
    if not msg_files:
        return total_files, moved_files, skipped_files, domain_counts
        
    thread_id = thread_dir.name.split("_")[1] if "_" in thread_dir.name else "unknown"
    logger.info(f"处理线程 {thread_id}，共 {len(msg_files)} 个邮件文件")
    
    # 1. 提取所有邮件信息
    items = []
    for msg_file in msg_files:
        try:
            email_info = extract_email_info(msg_file)
            if not email_info:
                continue
            
            # 即使正文为空，只要有附件或其他价值可能也需要保留，
            # 但这里我们主要处理文本去重。过短的邮件如果不包含关键信息可能会被误判，
            # 但在extract_email_info中并没有过滤短邮件，我们在去重逻辑中处理。
            
            items.append(email_info)
            
            # 统计域名 (保持原有逻辑)
            company_domain = thread_dir.parent.name
            if email_info.get('sender'):
                import re
                email_match = re.search(r'[\w\.-]+@([\w\.-]+\.\w+)', email_info['sender'])
                if email_match:
                    company_domain = email_match.group(1).lower()
            domain_counts[company_domain] = domain_counts.get(company_domain, 0) + 1
            
        except Exception as e:
            logger.error(f"处理邮件 {msg_file} 时出错: {e}")
            skipped_files += 1
    
    total_files = len(items)
    
    # 2. 排序策略 (关键修改)
    # 优先保留：内容最长的邮件。
    # 逻辑：最长的邮件通常包含了最完整的历史引用。
    # 排序：长度(降序) -> 日期(降序，即最新的在先)
    items.sort(key=lambda x: (
        -x['length'], 
        x.get('date').timestamp() if x.get('date') else 0
    ))
    
    # 3. 去重处理
    kept = []     # 决定保留的邮件 (Masters)
    removed = []  # 决定移动的邮件 (Duplicates/Subsets)
    
    for item in items:
        # 第一个处理的必定是保留的（因为它是最长的）
        if not kept:
            kept.append(item)
            continue
            
        is_duplicate = False
        duplicate_reason = ""
        
        # 拿当前邮件(item)与所有已保留的邮件(kept)对比
        # 只要 item 被任意一个 kept 邮件包含，item 就是冗余的
        for k in kept:
            is_subset, reason = check_if_subset(item, k, step_config)
            
            if is_subset:
                is_duplicate = True
                duplicate_reason = f"被 {k['path'].name} 包含 ({reason})"
                break
                
        if is_duplicate:
            logger.debug(f"判定重复: {item['path'].name} -> {duplicate_reason}")
            removed.append(item)
        else:
            # 如果没有被任何已有的邮件包含，说明它包含独特信息（或者是分支回复），保留
            kept.append(item)
    
    # 4. 移动重复文件
    for item in removed:
        try:
            dest_path = safe_move(item['path'])
            if dest_path:
                moved_files += 1
            else:
                skipped_files += 1
        except Exception as e:
            logger.error(f"移动重复邮件 {item['path']} 时出错: {e}")
            skipped_files += 1
            
    return total_files, moved_files, skipped_files, domain_counts

def check_if_subset(candidate: Dict, master: Dict, step_config: Dict) -> Tuple[bool, str]:
    """
    判断 candidate (短) 是否被 master (长) 所包含
    
    Args:
        candidate: 候选邮件（较短）
        master: 主邮件（较长，已保留）
        step_config: 配置
        
    Returns:
        (是否包含, 原因)
    """
    body_candidate = candidate['clean']
    body_master = master['clean']
    
    # 如果候选内容极短（例如只有"OK"），风险较高，可以加一个最小长度保护
    # 但根据你的需求，被包含的都应该移走，所以这里不做严格限制
    if len(body_candidate) < 5:
        return False, "内容太短忽略"

    # 1. 精确子串匹配 (最快且最准确)
    if exact_substring_match(body_candidate, body_master):
        return True, "精确包含"
    
    # 2. 分词连续匹配 (Tokenized Contiguous)
    # 这是处理引用符号(>)差异的关键。
    # 因为 clean_body 现在保留了引用内容，但 tokens() 会忽略标点，
    # 所以 "Hello" 能够匹配 "> Hello"
    if tokenized_contiguous_match(body_candidate, body_master):
        return True, "分词序列包含"
    
    # 3. 模糊相似度匹配 (Fuzzy)
    # 仅当配置允许且文本长度足够时使用，避免短文本误判
    fuzzy_threshold = step_config.get("threshold", 0.94)
    if len(body_candidate) > 50 and fuzzy_similarity_match(body_candidate, body_master, fuzzy_threshold):
        return True, f"模糊相似度包含({fuzzy_threshold})"
    
    return False, "无包含关系"

def extract_email_info(msg_file: Path) -> Optional[Dict]:
    """从.msg文件中提取邮件信息和正文"""
    logger = get_dedupe_logger("03_extract")
    try:
        import extract_msg
        msg = extract_msg.Message(msg_file)
        
        sender = getattr(msg, 'sender', None) or getattr(msg, 'from', None)
        subject = getattr(msg, 'subject', "") or ""
        
        date = None
        if hasattr(msg, 'date') and msg.date:
            date = msg.date
        elif hasattr(msg, 'sentOn') and msg.sentOn:
            date = msg.sentOn
            
        body = getattr(msg, 'body', "") or ""
        msg.close()
        
        cleaned_body = clean_body_text(body)
        
        return {
            'path': msg_file,
            'sender': sender,
            'subject': subject,
            'date': date,
            'clean': cleaned_body,
            'length': len(cleaned_body)
        }
    except Exception as e:
        logger.error(f"提取邮件信息 {msg_file} 时出错: {e}")
        return None

def save_summary(summary_data: Dict, output_path: Path) -> bool:
    """保存处理摘要到JSON文件"""
    logger = get_dedupe_logger("03_summary")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存处理摘要失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="邮件去重处理")
    parser.add_argument("-i", "--input", help="输入目录")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("-b", "--backup", help="备份目录")
    parser.add_argument("-n", "--dry-run", action="store_true", help="模拟运行")
    parser.add_argument("-p", "--processes", type=int, help="并行进程数")
    args = parser.parse_args()
    
    step_config = get_dedupe_config()
    
    if args.input: step_config["input_dir"] = args.input
    if args.output: step_config["output_dir"] = args.output
    if args.backup: step_config["backup_dir"] = args.backup
    if args.dry_run: step_config["dry_run"] = True
    if args.processes: step_config["processes"] = args.processes
    
    logger = get_dedupe_logger("03_main")
    TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    input_dir = Path(step_config["input_dir"])
    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        sys.exit(1)
    
    # 确保备份目录存在
    Path(step_config["backup_dir"]).mkdir(parents=True, exist_ok=True)
    Path(step_config["output_dir"]).mkdir(parents=True, exist_ok=True)
    
    # 收集需要处理的线程目录
    # 假设结构是 input_dir / company_domain / thread_xxx
    all_thread_dirs = []
    company_dirs = [d for d in input_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    for company_dir in company_dirs:
        thread_dirs = [d for d in company_dir.iterdir() if d.is_dir() and d.name.startswith("thread_")]
        all_thread_dirs.extend(thread_dirs)
    
    logger.info(f"找到 {len(company_dirs)} 个公司目录，共 {len(all_thread_dirs)} 个线程目录")
    
    num_processes = step_config.get("processes", multiprocessing.cpu_count())
    
    if num_processes > 1 and len(all_thread_dirs) > 0:
        logger.info(f"使用 {num_processes} 个进程并行处理")
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.map(process_thread_dir, all_thread_dirs)
    else:
        logger.info("使用单进程处理")
        results = [process_thread_dir(d) for d in all_thread_dirs]
    
    # 汇总
    total_files = sum(r[0] for r in results)
    total_moved = sum(r[1] for r in results)
    total_skipped = sum(r[2] for r in results)
    all_domain_counts = {}
    for _, _, _, d_counts in results:
        for domain, count in d_counts.items():
            all_domain_counts[domain] = all_domain_counts.get(domain, 0) + count
            
    summary = {
        "timestamp": TIMESTAMP,
        "total_files": total_files,
        "moved_files": total_moved,
        "skipped_files": total_skipped,
        "domain_counts": all_domain_counts
    }
    
    summary_file = Path(step_config["output_dir"]) / f"dedupe_summary_{TIMESTAMP}.json"
    save_summary(summary, summary_file)
    
    logger.info(f"处理完成: 总文件 {total_files}, 移动重复 {total_moved}")
    logger.info(f"摘要已保存: {summary_file}")

if __name__ == "__main__":
    main()