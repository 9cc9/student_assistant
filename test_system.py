"""AI助教评估系统测试脚本"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from src.models.assessment import Deliverables
from src.services.assessment_service import AssessmentService
from src.services.gateway_service import GatewayService


class SystemTester:
    """系统功能测试器"""
    
    def __init__(self):
        self.gateway_service = GatewayService()
        
    async def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始AI助教评估系统综合测试")
        print("=" * 50)
        
        # 测试数据
        test_data = self._get_test_data()
        
        try:
            # 1. 提交评估请求
            print("\n1️⃣ 测试评估提交...")
            submit_result = await self._test_submit_assessment(test_data)
            assessment_id = submit_result["assessment_id"]
            print(f"✅ 评估提交成功，ID: {assessment_id}")
            
            # 2. 查询评估状态（初始状态）
            print("\n2️⃣ 测试状态查询...")
            initial_status = await self._test_get_status(assessment_id)
            print(f"✅ 初始状态: {initial_status['status']}")
            
            # 3. 等待评估完成
            print("\n3️⃣ 等待评估完成...")
            final_result = await self._wait_for_completion(assessment_id)
            
            if final_result["status"] == "completed":
                print("✅ 评估完成！")
                self._print_assessment_results(final_result)
                
                # 4. 测试准出规则导出
                print("\n4️⃣ 测试准出规则导出...")
                export_result = await self._test_export_rules(assessment_id)
                print(f"✅ 规则导出成功: {export_result['path_engine_ref']}")
                
            else:
                print(f"❌ 评估失败: {final_result}")
            
            # 5. 测试系统状态
            print("\n5️⃣ 测试系统状态...")
            system_status = self._test_system_status()
            print(f"✅ 系统状态: {system_status['status']}")
            
            # 6. 测试统计信息
            print("\n6️⃣ 测试统计信息...")
            statistics = self._test_statistics()
            print(f"✅ 统计信息获取成功，总评估数: {statistics['total_assessments']}")
            
            print("\n🎉 所有测试完成！")
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
    
    async def _test_submit_assessment(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """测试提交评估"""
        return await self.gateway_service.submit_for_assessment(test_data)
    
    async def _test_get_status(self, assessment_id: str) -> Dict[str, Any]:
        """测试获取状态"""
        return await self.gateway_service.get_assessment_result(assessment_id)
    
    async def _wait_for_completion(self, assessment_id: str, max_wait: int = 300) -> Dict[str, Any]:
        """等待评估完成"""
        wait_time = 0
        while wait_time < max_wait:
            result = await self._test_get_status(assessment_id)
            
            if result["status"] in ["completed", "failed"]:
                return result
            
            print(f"⏳ 评估进行中... ({wait_time}s)")
            await asyncio.sleep(10)
            wait_time += 10
        
        raise Exception("评估超时")
    
    async def _test_export_rules(self, assessment_id: str) -> Dict[str, Any]:
        """测试导出规则"""
        return await self.gateway_service.sync_to_path_engine(assessment_id)
    
    def _test_system_status(self) -> Dict[str, Any]:
        """测试系统状态"""
        return self.gateway_service.get_system_status()
    
    def _test_statistics(self) -> Dict[str, Any]:
        """测试统计信息"""
        return self.gateway_service.get_statistics(7)
    
    def _get_test_data(self) -> Dict[str, Any]:
        """获取测试数据"""
        return {
            "student_id": "test_student_001",
            "deliverables": {
                "idea_text": """
                项目名称：智能学习助手
                
                项目概述：
                开发一个基于AI的个性化学习助手应用，帮助学生制定学习计划、跟踪进度、提供答疑服务。
                
                目标用户：
                - 大学生和研究生
                - 自学者和终身学习者
                - 在线教育平台的用户
                
                核心功能：
                1. 智能学习计划生成：根据用户目标和时间安排生成个性化学习路径
                2. 进度跟踪与分析：记录学习数据，提供进度分析和建议
                3. AI答疑助手：支持多学科的智能问答
                4. 知识图谱可视化：展示知识点之间的关联关系
                5. 社区互动：学习小组、讨论区、经验分享
                
                技术栈：
                - 前端：React + TypeScript + Ant Design
                - 后端：Python + FastAPI + SQLAlchemy
                - AI服务：阿里云通义千问 + LangChain
                - 数据库：PostgreSQL + Redis
                - 部署：Docker + Kubernetes
                
                创新点：
                - 结合学习科学和认知心理学理论设计学习算法
                - 使用多模态AI技术支持图像、音频等多种学习内容
                - 引入游戏化元素提升学习动机
                
                商业模式：
                - 基础功能免费，高级功能订阅制
                - 与教育机构合作提供定制化服务
                """,
                "ui_images": [
                    # 这里应该是base64编码的图片，为了测试使用占位符
                    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                ],
                "code_repo": "https://github.com/test-user/smart-learning-assistant",
                "code_snippets": [
                    '''
# 智能学习助手 - 主要服务类
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import openai

class LearningPlan(BaseModel):
    """学习计划模型"""
    student_id: str
    subject: str
    goals: List[str]
    timeline: int  # 天数
    difficulty_level: str

class LearningAssistant:
    """学习助手核心服务"""
    
    def __init__(self):
        self.app = FastAPI(title="Smart Learning Assistant")
        # 使用阿里云通义千问API
    
    async def create_learning_plan(self, plan_data: LearningPlan) -> dict:
        """创建个性化学习计划"""
        try:
            # 使用AI生成学习计划
            prompt = f"""
            为学生创建一个{plan_data.timeline}天的{plan_data.subject}学习计划。
            学习目标：{', '.join(plan_data.goals)}
            难度级别：{plan_data.difficulty_level}
            
            请提供详细的日程安排和学习建议。
            """
            
            # 这里应该调用阿里云通义千问API
            # 在实际项目中通过评估器基类调用
            
            plan = "基于阿里云通义千问生成的学习计划"  # 模拟结果
            
            return {
                "status": "success",
                "student_id": plan_data.student_id,
                "learning_plan": plan,
                "created_at": "2024-01-01T00:00:00Z"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def track_progress(self, student_id: str) -> dict:
        """跟踪学习进度"""
        # 这里应该从数据库获取实际进度数据
        return {
            "student_id": student_id,
            "completion_rate": 0.65,
            "current_topic": "机器学习基础",
            "next_milestone": "完成线性回归实践",
            "study_streak": 7
        }
    
    def get_ai_tutor_response(self, question: str) -> str:
        """AI答疑功能 - 使用阿里云通义千问"""
        try:
            # 在实际项目中会通过评估器基类调用阿里云通义千问API
            return f"基于阿里云通义千问的回答：{question}"
        except Exception as e:
            return f"抱歉，无法处理您的问题：{str(e)}"

# FastAPI路由定义
app = FastAPI()
assistant = LearningAssistant()

@app.post("/api/learning-plan")
async def create_plan(plan: LearningPlan):
    return await assistant.create_learning_plan(plan)

@app.get("/api/progress/{student_id}")  
async def get_progress(student_id: str):
    return await assistant.track_progress(student_id)

@app.post("/api/ask")
async def ask_tutor(question: dict):
    return {"answer": assistant.get_ai_tutor_response(question["text"])}
                    '''
                ]
            }
        }
    
    def _print_assessment_results(self, result: Dict[str, Any]):
        """打印评估结果"""
        print(f"\n📊 评估结果详情:")
        print(f"   总分: {result.get('overall_score', 0):.1f}")
        
        if "breakdown" in result:
            breakdown = result["breakdown"]
            print(f"   📝 创意评分: {breakdown.get('idea', 0):.1f}")
            print(f"   🎨 UI评分: {breakdown.get('ui', 0):.1f}")
            print(f"   💻 代码评分: {breakdown.get('code', 0):.1f}")
        
        if "diagnosis" in result and result["diagnosis"]:
            print(f"\n🔧 主要诊断建议:")
            for i, diag in enumerate(result["diagnosis"][:3], 1):
                print(f"   {i}. [{diag['dim']}] {diag['issue']}")
                print(f"      建议: {diag['fix']}")
        
        if "exit_rules" in result and result["exit_rules"]:
            rules = result["exit_rules"]
            status = "✅ 通过" if rules.get("pass") else "⚠️ 需改进"
            print(f"\n🎯 准出状态: {status}")


async def main():
    """主测试函数"""
    tester = SystemTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())


