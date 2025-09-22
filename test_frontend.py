#!/usr/bin/env python3
"""
测试前端页面修复效果
"""

import asyncio
import json
import time
from src.services.assessment_service import AssessmentService

async def test_frontend_fix():
    """测试前端修复效果"""
    
    print("🧪 === 前端页面修复测试 ===")
    
    service = AssessmentService()
    
    # 创建一个简单的测试项目
    test_data = {
        "idea_text": "一个简单的计算器App，支持基本的四则运算",
        "project_name": "计算器",
        "technical_stack": ["JavaScript", "HTML", "CSS"],
        "target_users": "学生",
        "code_snippets": [
            """// calculator.js
function add(a, b) {
    return a + b;
}

function calculate() {
    const num1 = parseFloat(document.getElementById('num1').value);
    const num2 = parseFloat(document.getElementById('num2').value);
    const result = add(num1, num2);
    document.getElementById('result').textContent = result;
}"""
        ]
    }
    
    print("📝 提交测试评估...")
    assessment_id = await service.submit_assessment("frontend_test", test_data)
    print(f"✅ 评估ID: {assessment_id}")
    
    print("\n📊 模拟前端轮询过程:")
    
    # 模拟前端的轮询行为
    for i in range(10):
        try:
            status = service.get_assessment_status(assessment_id)
            current_status = status['status']
            
            print(f"🔄 第{i+1}次轮询 - 状态: {current_status}")
            
            if current_status == 'completed':
                print(f"🎉 评估完成！总分: {status.get('overall_score', 0):.1f}/100")
                
                # 模拟前端状态显示
                breakdown = status.get('breakdown', {})
                if breakdown:
                    print(f"📋 分项得分:")
                    print(f"  💡 创意: {breakdown.get('idea', 0):.1f}/100")
                    print(f"  🎨 UI: {breakdown.get('ui', 0):.1f}/100")
                    print(f"  💻 代码: {breakdown.get('code', 0):.1f}/100")
                
                # 保存结果供前端测试
                with open("frontend_test_result.json", "w", encoding="utf-8") as f:
                    json.dump(status, f, indent=2, ensure_ascii=False)
                
                print("📄 结果已保存到 frontend_test_result.json")
                print("\n🌐 现在可以打开浏览器访问 http://localhost:8000 测试页面功能")
                print("   - 状态应该自动从'评估中'变为'已完成'")
                print("   - 刷新状态按钮应该正常工作")
                print("   - 查看评估结果按钮应该显示详细结果")
                break
                
            elif current_status == 'failed':
                print("❌ 评估失败")
                break
            
            await asyncio.sleep(2)  # 模拟3秒轮询间隔
            
        except Exception as e:
            print(f"⚠️ 轮询出错: {str(e)}")
            break
    
    print("\n✅ 前端修复测试完成!")
    print("🔗 访问 http://localhost:8000 查看修复效果")

if __name__ == "__main__":
    asyncio.run(test_frontend_fix())
