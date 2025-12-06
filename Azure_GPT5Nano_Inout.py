import os
import sys
from openai import AzureOpenAI

# 初始化Azure OpenAI客户端
def init_client():
    """初始化Azure OpenAI客户端"""
    return AzureOpenAI(
        api_key="7",
        azure_endpoint="https://admin-mew591uw-eastus2.openai.azure.com",
        api_version="2025-01-01-preview"
    )

# 获取GPT-5模型响应
def get_gpt5_response(system_prompt, user_prompt):
    """
    获取GPT-5模型的响应
    
    参数:
    system_prompt (str): 系统提示词
    user_prompt (str): 用户提示词
    
    返回:
    str: 模型生成的响应内容
    """
    try:
        # 初始化客户端
        client = init_client()
        
        # 发送请求
        response = client.chat.completions.create(
            model="gpt-5-nano", # model = "deployment_name".
            temperature=1,  # 修改为默认值1，因为GPT-5-nano不支持temperature=0
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # 返回响应内容
        return response.choices[0].message.content
        
    except Exception as e:
        return f"发生错误: {str(e)}"

# 处理Markdown文件的函数，与SiliconFlow接口保持一致
def process_markdown_with_ai(content, system_prompt):
    """
    使用Azure GPT-5-nano处理Markdown内容
    
    参数:
    content (str): 带行号的Markdown内容
    system_prompt (str): 系统提示词
    
    返回:
    str: 模型生成的响应内容
    """
    return get_gpt5_response(system_prompt, content)

# 主函数，用于直接运行脚本
def main():
    """主函数，处理命令行参数并获取模型响应"""
    # 检查命令行参数数量
    # 要求必须提供两个参数：系统提示词和用户提示词
    if len(sys.argv) != 3:
        print("请输出参数以调用大模型")
        print("使用方法: python Azure_GPT5Nano_Inout.py \"系统提示词\" \"用户提示词\"")
        return
    
    # 获取命令行参数
    system_prompt = sys.argv[1]
    user_prompt = sys.argv[2]
    
    # 验证参数不为空
    if not system_prompt or not user_prompt:
        print("请输出参数以调用大模型")
        print("使用方法: python Azure_GPT5Nano_Inout.py \"系统提示词\" \"用户提示词\"")
        return
    
    # 获取响应并打印
    response = get_gpt5_response(system_prompt, user_prompt)
    print(response)

# 如果作为脚本直接运行，则执行主函数
if __name__ == "__main__":
    main()