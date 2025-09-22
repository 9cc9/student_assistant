"""阿里云通义千问API集成测试脚本"""
import asyncio
import os
from dotenv import load_dotenv
import dashscope
from dashscope import Generation

# 加载环境变量
load_dotenv()

async def test_qwen_api():
    """测试阿里云通义千问API"""
    
    print("🚀 开始测试阿里云通义千问API集成")
    print("=" * 50)
    
    # 设置API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 错误：请设置DASHSCOPE_API_KEY环境变量")
        print("   您可以在阿里云控制台获取API密钥：https://dashscope.console.aliyun.com/")
        return
    
    dashscope.api_key = api_key
    print(f"✅ API密钥已设置 (前8位: {api_key[:8]}...)")
    
    # 测试基础API调用
    print("\n1️⃣ 测试基础API调用...")
    try:
        response = Generation.call(
            model='qwen-turbo',  # 使用turbo模型测试，更便宜
            prompt='你好，请简单介绍一下你自己。',
            max_tokens=100,
            temperature=0.1
        )
        
        if response.status_code == 200:
            print(f"✅ 基础调用成功！")
            print(f"   回复: {response.output.text[:100]}...")
        else:
            print(f"❌ API调用失败: {response.message}")
            return
            
    except Exception as e:
        print(f"❌ 基础调用异常: {str(e)}")
        return
    
    # 测试评估场景
    print("\n2️⃣ 测试评估场景...")
    
    evaluation_prompt = """
    请评估以下学生项目创意，从三个维度进行评分（0-100分）：

    1. 创新性（新颖度/前沿性）
    2. 可行性（技术难度/周期/资源）  
    3. 学习价值（技能提升/知识拓展）

    学生创意：开发一个基于AI的个性化学习助手应用，帮助学生制定学习计划、跟踪进度、提供答疑服务。
    技术栈：React, Python, FastAPI, OpenAI GPT
    目标用户：大学生和研究生
    核心功能：智能学习计划生成、进度跟踪与分析、AI答疑助手

    请返回JSON格式：
    {
      "innovation": 分数,
      "feasibility": 分数,
      "learning_value": 分数,
      "feedback": "详细反馈",
      "suggestions": ["改进建议1", "改进建议2"]
    }
    """
    
    try:
        response = Generation.call(
            model='qwen-turbo',
            prompt=evaluation_prompt,
            max_tokens=800,
            temperature=0.1
        )
        
        if response.status_code == 200:
            print(f"✅ 评估场景测试成功！")
            print(f"   回复长度: {len(response.output.text)} 字符")
            print(f"   前200字符: {response.output.text[:200]}...")
            
            # 尝试解析JSON
            try:
                import json
                # 提取JSON部分
                text = response.output.text
                start_idx = text.find('{')
                end_idx = text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = text[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    print(f"   JSON解析成功: 包含 {len(parsed)} 个字段")
                else:
                    print("   JSON提取失败，可能需要优化提示词")
            except Exception as e:
                print(f"   JSON解析异常: {str(e)}")
        else:
            print(f"❌ 评估场景测试失败: {response.message}")
            
    except Exception as e:
        print(f"❌ 评估场景测试异常: {str(e)}")
    
    # 测试异步调用
    print("\n3️⃣ 测试异步调用...")
    
    async def async_call_qwen(prompt: str):
        """异步调用通义千问"""
        def _sync_call():
            return Generation.call(
                model='qwen-turbo',
                prompt=prompt,
                max_tokens=100,
                temperature=0.1
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)
    
    try:
        response = await async_call_qwen("请用一句话描述人工智能的发展趋势。")
        if response.status_code == 200:
            print(f"✅ 异步调用成功！")
            print(f"   回复: {response.output.text}")
        else:
            print(f"❌ 异步调用失败: {response.message}")
            
    except Exception as e:
        print(f"❌ 异步调用异常: {str(e)}")
    
    # 测试模型列表
    print("\n4️⃣ 可用模型信息:")
    print("   - qwen-turbo: 通用模型，速度快，成本低")
    print("   - qwen-plus: 增强模型，效果更好")  
    print("   - qwen-max: 最强模型，效果最佳")
    print("   建议在开发测试时使用 qwen-turbo，生产环境可选择 qwen-plus 或 qwen-max")
    
    print("\n🎉 阿里云通义千问API测试完成！")
    print("\n💡 使用建议：")
    print("   1. 确保API密钥有足够的余额")
    print("   2. 根据需要选择合适的模型")
    print("   3. 合理设置temperature和top_p参数")
    print("   4. 处理好API限流和异常情况")


def test_environment_setup():
    """测试环境配置"""
    print("🔧 检查环境配置...")
    
    # 检查必要的包
    try:
        import dashscope
        print("✅ dashscope 包已安装")
    except ImportError:
        print("❌ dashscope 包未安装，请运行: pip install dashscope")
        return False
    
    # 检查API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ DASHSCOPE_API_KEY 环境变量未设置")
        print("   请在 .env 文件中添加: DASHSCOPE_API_KEY=your_api_key_here")
        return False
    else:
        print(f"✅ DASHSCOPE_API_KEY 已设置")
    
    return True


if __name__ == "__main__":
    print("🧪 阿里云通义千问API集成测试")
    print("=" * 60)
    
    if test_environment_setup():
        asyncio.run(test_qwen_api())
    else:
        print("\n❌ 环境配置检查失败，请修复后重试")
