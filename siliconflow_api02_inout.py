from openai import OpenAI
import sys

def get_ai_response(user_prompt="介绍你自己，你是推理模型还是对话模型", system_prompt=None):
    """
    调用硅基流动API获取AI响应
    
    参数:
        user_prompt (str): 用户提示词，默认为"介绍你自己"
        system_prompt (str, optional): 系统提示词，如果为None则忽略
    
    返回:
        str: AI的响应内容
    """
    try:
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key="sk-rnch", 
            base_url="https://api.siliconflow.cn/v1"
        )
        
        # 构建消息列表
        messages = []
        
        # 如果提供了系统提示词，则添加到消息列表
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        
        # 添加用户提示词
        messages.append({'role': 'user', 'content': user_prompt})
        
        # 调用API获取响应
        response = client.chat.completions.create(
            # #model="Qwen/Qwen2.5-72B-Instruct",
            # model="THUDM/glm-4-9b-chat",
            # messages=messages,
            # stream=False  # 非流式输出
            model="Qwen/Qwen3-Next-80B-A3B-Instruct",
            messages=messages,
            stream=False,
            temperature=0.0,       # 更确定、更“规则化”的输出
            top_p=0.9,             # 常规控制采样范围
            #top_k=50,              # 明确限制采样候选，防止发散
            #max_tokens=16384,      # 足够覆盖最长邮件
            frequency_penalty=0.5  # 减少重复语句/空行/尾部花字
        )
        
        # 提取响应内容
        if hasattr(response, 'choices') and response.choices:
            if hasattr(response.choices[0], 'message'):
                content = []
                if hasattr(response.choices[0].message, 'content'):
                    content.append(response.choices[0].message.content)
                # 检查是否有reasoning_content
                if hasattr(response.choices[0].message, 'reasoning_content'):
                    content.append(response.choices[0].message.reasoning_content)
                
                # 返回完整响应内容，用换行符连接
                return '\n'.join(content) if content else "未获取到响应内容"
        
        return "未获取到响应内容"
        
    except Exception as e:
        return f"API调用出错: {str(e)}"

if __name__ == "__main__":
    """
    当脚本直接运行时的处理逻辑
    支持从命令行参数获取用户提示词和系统提示词
    格式: python siliconflow_api02_inout.py [用户提示词] [系统提示词]
    """
    # 默认参数
    user_prompt = "介绍你自己"
    system_prompt = None
    
    # 从命令行参数获取输入
    if len(sys.argv) > 1:
        user_prompt = sys.argv[1]
    if len(sys.argv) > 2:
        system_prompt = sys.argv[2]
    
    # 调用函数获取响应
    result = get_ai_response(user_prompt, system_prompt)
    
    # 打印结果（当直接运行脚本时）
    print(result)