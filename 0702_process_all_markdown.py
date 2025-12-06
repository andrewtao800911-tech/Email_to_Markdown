import os
import json
import re
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

# 导入AI处理模块
# 注释掉SiliconFlow，改用Azure GPT-5-nano
# try:
#     from siliconflow_api02_inout import process_markdown_with_ai
# except ImportError:
try:
    from Azure_GPT5Nano_Inout import process_markdown_with_ai
except ImportError as e:
    print(f"无法导入AI处理模块: {e}")
    print("请确保Azure_GPT5Nano_Inout.py文件在当前目录或Python路径中")
    sys.exit(1)

def load_system_prompt():
    """加载系统提示词"""
    # 获取当前脚本所在目录
    script_dir = Path(__file__).parent
    # 使用与脚本同名的文件，但扩展名为.md
    script_name = Path(__file__).stem
    prompt_path = script_dir / f"{script_name}.md"
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"系统提示词文件未找到: {prompt_path}")
    except Exception as e:
        raise Exception(f"读取系统提示词文件失败: {str(e)}")

def extract_json_from_response(response_text):
    """从AI响应中提取JSON内容"""
    # 尝试直接解析整个响应
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取JSON代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试提取花括号内容
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    raise ValueError("无法从AI响应中提取有效的JSON")

def process_single_file(file_path, system_prompt, logger):
    """处理单个MD文件"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 调用AI处理
        response = process_markdown_with_ai(content, system_prompt)
        
        # 添加调试信息
        logger.info(f"AI响应: {response}")
        
        # 提取JSON标记
        json_markers = extract_json_from_response(response)
        
        # 如果AI返回空响应，创建一个空数组
        if json_markers is None:
            json_markers = []
            logger.info(f"AI返回空响应，创建空数组")
        
        return json_markers
        
    except Exception as e:
        logger.error(f"处理文件失败 {file_path}: {str(e)}")
        return None

def save_json_markers(json_markers, output_path, logger):
    """保存JSON标记到文件"""
    try:
        # 确保输出目录存在
        if isinstance(output_path, str):
            output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_markers, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON标记已保存到: {output_path}")
        return True
    except Exception as e:
        logger.error(f"保存JSON标记失败 {output_path}: {str(e)}")
        return False

def main():
    # 获取步骤配置和日志记录器
    step_config = get_step_config("07")
    logger = get_logger("07", "0702_process_all_markdown.py")
    
    # 记录处理开始
    logger.log_start()
    
    try:
        # 使用配置文件中的路径
        input_dir = step_config["numbered_dir"]
        output_dir = step_config["json_dir"]  # 使用json_dir作为输出目录
        
        # 确保输出目录存在
        ensure_dir(output_dir)
        
        # 加载系统提示词
        system_prompt = load_system_prompt()
        logger.info(f"已加载系统提示词: {step_config['system_prompt']}")
        
        # 获取所有MD文件
        md_files = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
        
        if not md_files:
            logger.warning(f"在目录 {input_dir} 中未找到MD文件")
            logger.log_end(False, "未找到MD文件")
            return
        
        logger.info(f"找到 {len(md_files)} 个MD文件，开始AI处理...")
        
        success_count = 0
        failure_count = 0
        
        for i, md_file in enumerate(md_files, 1):
            try:
                # 计算相对路径，保持目录结构
                rel_path = os.path.relpath(md_file, input_dir)
                # 将.md扩展名改为.json
                json_path = os.path.splitext(rel_path)[0] + '.json'
                output_path = os.path.join(output_dir, json_path)
                
                logger.info(f"[{i}/{len(md_files)}] 正在处理: {rel_path}")
                
                # 处理文件
                json_markers = process_single_file(md_file, system_prompt, logger)
                
                if json_markers:
                    # 保存结果
                    if save_json_markers(json_markers, output_path, logger):
                        success_count += 1
                    else:
                        failure_count += 1
                else:
                    failure_count += 1
                
            except Exception as e:
                logger.error(f"处理文件失败 {md_file}: {str(e)}")
                failure_count += 1
        
        logger.info(f"AI处理完成！成功: {success_count}, 失败: {failure_count}")
        logger.log_end(True, f"成功处理 {success_count} 个文件，失败 {failure_count} 个文件")
        
    except Exception as e:
        logger.log_end(False, f"处理过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()