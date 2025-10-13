"""
个性化学习路径推荐系统演示脚本

演示完整的学习流程：
1. 入学诊断 -> 2. 生成学生画像 -> 3. 初始化学习路径 -> 4. AI助教评估 -> 5. 路径调整推荐

运行命令：python demo_learning_path.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.services.diagnostic_service import DiagnosticService
from src.services.learning_path_service import LearningPathService
from src.services.path_recommendation_engine import PathRecommendationEngine
from src.models.learning_path import Channel, NodeStatus
from src.models.student import LearningLevel, LearningStyle


async def demo_complete_learning_journey():
    """演示完整的学习旅程"""
    
    print("🚀 个性化学习路径推荐系统演示")
    print("=" * 60)
    
    # 初始化服务
    diagnostic_service = DiagnosticService()
    learning_path_service = LearningPathService()
    recommendation_engine = PathRecommendationEngine()
    
    # 模拟学生信息
    student_id = "demo_student_001"
    print(f"👤 演示学生ID: {student_id}")
    print()
    
    # ========== 步骤1: 入学诊断 ==========
    print("📋 步骤1: 入学诊断测试")
    print("-" * 30)
    
    # 获取诊断测试
    diagnostic_test = diagnostic_service.get_diagnostic_test()
    print(f"📝 测试包含 {len(diagnostic_test['sections'])} 个部分，预计耗时 {diagnostic_test['test_info']['estimated_time']}")
    
    # 模拟学生回答（这里使用预设答案）
    student_responses = {
        "concepts": {
            "concept_1": "A",  # 正确答案
            "concept_2": "A",  # 正确答案
            "concept_3": "B",  # 正确答案
            "concept_4": "A",  # 错误答案，应该是B
            "concept_5": "前端负责用户界面，后端负责数据处理"
        },
        "coding": {
            "code_1": "def find_max(numbers):\n    return max(numbers)",
            "code_2": "def fetch_data(url):\n    try:\n        response = requests.get(url)\n        return response.json()\n    except:\n        return None",
            "code_3": "输出[1,2,3,4]，因为y和x是同一个列表对象的引用"
        },
        "tools": {
            "Python": 4,  # 1-5评分
            "JavaScript": 2,
            "Git": 3,
            "Docker": 1,
            "HTML/CSS": 3,
            "React/Vue": 2,
            "OpenAI API": 1,
            "LangChain": 1
        },
        "preferences": {
            "learning_style": "examples_first",
            "time_budget": 8,
            "interests": ["RAG", "Agent"],
            "goals": ["完成RAG应用", "掌握全栈开发"],
            "challenges": "debugging"
        }
    }
    
    # 评估诊断结果
    diagnostic_results = diagnostic_service.evaluate_diagnostic_results(student_responses)
    print(f"📊 诊断评估完成:")
    print(f"   概念理解: {diagnostic_results['concept_score']}/100")
    print(f"   编程能力: {diagnostic_results['coding_score']}/100")
    print(f"   工具熟悉度: {diagnostic_results['tool_familiarity']}/100")
    print(f"   整体准备度: {diagnostic_results['overall_readiness']}")
    print(f"   学习风格: {diagnostic_results['learning_style_preference']}")
    print(f"   时间预算: {diagnostic_results['time_budget_hours_per_week']}小时/周")
    print(f"   兴趣领域: {', '.join(diagnostic_results['interests'])}")
    print()
    
    # ========== 步骤2: 生成学生画像 ==========
    print("👤 步骤2: 生成学生画像")
    print("-" * 30)
    
    student_profile = await learning_path_service.create_student_profile(student_id, diagnostic_results)
    print(f"📋 学生画像已创建:")
    print(f"   学习水平: {student_profile.level.value}")
    print(f"   薄弱技能: {', '.join(student_profile.weak_skills)}")
    print(f"   兴趣方向: {', '.join(student_profile.interests)}")
    print(f"   学习风格: {student_profile.learning_style.value}")
    print()
    
    # ========== 步骤3: 初始化学习路径 ==========
    print("🛤️ 步骤3: 初始化学习路径")
    print("-" * 30)
    
    progress = await learning_path_service.initialize_student_path(student_id, student_profile)
    print(f"📍 学习路径已初始化:")
    print(f"   起始节点: {progress.current_node_id}")
    print(f"   推荐通道: {progress.current_channel.value}")
    print(f"   可用节点: {list(progress.node_statuses.keys())}")
    print()
    
    # 获取初始路径推荐
    initial_recommendation = await recommendation_engine.recommend_initial_path(student_profile, diagnostic_results)
    print(f"🎯 初始路径推荐:")
    print(f"   推荐通道: {initial_recommendation['recommended_channel'].value}")
    print(f"   学习策略: {initial_recommendation['learning_strategy']['style_adaptation']['approach']}")
    print(f"   预计时间线: {initial_recommendation['estimated_timeline']['total_weeks']} 周")
    print()
    
    # ========== 步骤4: 查看课程节点详情 ==========
    print("📚 步骤4: 课程节点信息")
    print("-" * 30)
    
    learning_path = learning_path_service.get_learning_path()
    print(f"📖 课程: {learning_path.name}")
    print(f"📋 节点序列:")
    for node in learning_path.nodes:
        current_indicator = "👉 " if node.id == progress.current_node_id else "   "
        channel = progress.current_channel
        task = node.channel_tasks[channel]["task"]
        hours = node.estimated_hours[channel]
        print(f"{current_indicator}{node.order}. {node.name} ({channel.value}通道, {hours}h)")
        print(f"      任务: {task}")
    print()
    
    # ========== 步骤5: 模拟作业提交和AI助教评估 ==========
    print("🤖 步骤5: 模拟作业提交与AI助教评估")
    print("-" * 30)
    
    # 模拟评估结果（这里使用预设的结果）
    mock_assessment_result = {
        "overall_score": 78,
        "breakdown": {
            "idea": 75,
            "ui": 80,
            "code": 82
        },
        "diagnosis": [
            {"dimension": "code.testing", "issue": "单元测试覆盖率偏低", "fix": "增加关键功能的单元测试"},
            {"dimension": "idea.feasibility", "issue": "技术实现方案需要更详细", "fix": "补充具体的技术架构说明"}
        ]
    }
    
    print(f"📝 模拟作业评估结果:")
    print(f"   综合得分: {mock_assessment_result['overall_score']}/100")
    print(f"   Idea得分: {mock_assessment_result['breakdown']['idea']}/100")
    print(f"   UI得分: {mock_assessment_result['breakdown']['ui']}/100") 
    print(f"   代码得分: {mock_assessment_result['breakdown']['code']}/100")
    print(f"   诊断问题: {len(mock_assessment_result['diagnosis'])}个")
    print()
    
    # ========== 步骤6: 自动路径调整 ==========
    print("🔄 步骤6: 基于评估结果的路径调整")
    print("-" * 30)
    
    # 更新学生进度（假设完成了当前节点）
    await learning_path_service.update_student_progress(
        student_id=student_id,
        node_id=progress.current_node_id,
        status=NodeStatus.COMPLETED,
        assessment_result=mock_assessment_result
    )
    
    # 生成路径推荐
    recommendation = await learning_path_service.recommend_next_step(
        student_id=student_id,
        assessment_result=mock_assessment_result
    )
    
    print(f"🎯 路径推荐结果:")
    print(f"   推荐决策: {recommendation.decision.value}")
    print(f"   推荐通道: {recommendation.recommended_channel.value}")
    print(f"   下一节点: {recommendation.next_node_id}")
    print(f"   推荐理由: {recommendation.reasoning}")
    print(f"   预估时间: {recommendation.estimated_completion_time}小时")
    print()
    
    if recommendation.scaffold_resources:
        print(f"📖 推荐资源: {', '.join(recommendation.scaffold_resources)}")
        print()
    
    # ========== 步骤7: 查看更新后的学习进度 ==========
    print("📈 步骤7: 学习进度概览")
    print("-" * 30)
    
    updated_progress = learning_path_service.get_student_progress(student_id)
    completion_rate = len(updated_progress.completed_nodes) / len(learning_path.nodes) * 100
    
    print(f"📊 学习进度统计:")
    print(f"   完成节点: {len(updated_progress.completed_nodes)}/{len(learning_path.nodes)}")
    print(f"   完成率: {completion_rate:.1f}%")
    print(f"   当前节点: {updated_progress.current_node_id}")
    print(f"   当前通道: {updated_progress.current_channel.value}")
    print(f"   总学习时长: {updated_progress.total_study_hours}小时")
    print(f"   掌握度分数: {dict(list(updated_progress.mastery_scores.items())[:3])}...")
    print()
    
    # ========== 步骤8: 高级推荐分析 ==========
    print("🔍 步骤8: 高级路径推荐分析")
    print("-" * 30)
    
    # 模拟历史评估数据
    recent_assessments = [
        {"overall_score": 65, "breakdown": {"idea": 60, "ui": 70, "code": 65}},
        {"overall_score": 72, "breakdown": {"idea": 70, "ui": 75, "code": 70}}, 
        {"overall_score": 78, "breakdown": {"idea": 75, "ui": 80, "code": 82}}
    ]
    
    # 模拟学习行为数据
    behavioral_data = {
        "weekly_study_hours": [6, 8, 7, 9],
        "submission_pattern": "regular",
        "help_requests": 2
    }
    
    advanced_recommendation = await recommendation_engine.recommend_path_adjustment(
        student_id=student_id,
        current_progress={"current_channel": progress.current_channel.value},
        recent_assessments=recent_assessments,
        behavioral_data=behavioral_data
    )
    
    print(f"🧠 高级推荐分析:")
    print(f"   调整类型: {advanced_recommendation['adjustment_type']}")
    print(f"   置信度: {advanced_recommendation['confidence_score']:.2f}")
    print(f"   表现趋势: {advanced_recommendation['current_analysis']['performance']['trend']}")
    print(f"   参与度: {advanced_recommendation['current_analysis']['behavior_patterns']['engagement']}")
    print(f"   推荐行动: {advanced_recommendation['recommended_actions'][0]}")
    print()
    
    # ========== 总结 ==========
    print("✅ 演示完成总结")
    print("=" * 60)
    print("🎉 个性化学习路径推荐系统演示完成！")
    print()
    print("系统特点:")
    print("• ✅ 基于入学诊断的个性化画像生成")
    print("• ✅ 固定节点+可变通道的灵活路径机制")
    print("• ✅ AI助教评估与路径推荐的深度集成")
    print("• ✅ 实时的学习进度跟踪和调整")
    print("• ✅ 基于学习行为的智能推荐分析")
    print()
    print("适用场景:")
    print("• 🎓 本科AI课程的个性化教学")
    print("• 📚 在线教育平台的路径推荐")
    print("• 🏢 企业培训的个性化学习方案")
    print()
    
    # 保存演示结果
    demo_results = {
        "student_id": student_id,
        "diagnostic_results": diagnostic_results,
        "student_profile": {
            "level": student_profile.level.value,
            "weak_skills": student_profile.weak_skills,
            "interests": student_profile.interests,
            "learning_style": student_profile.learning_style.value,
            "time_budget": student_profile.time_budget_hours_per_week
        },
        "learning_progress": {
            "completed_nodes": updated_progress.completed_nodes,
            "current_node": updated_progress.current_node_id,
            "current_channel": updated_progress.current_channel.value,
            "completion_rate": completion_rate
        },
        "final_recommendation": {
            "decision": recommendation.decision.value,
            "channel": recommendation.recommended_channel.value,
            "next_node": recommendation.next_node_id,
            "reasoning": recommendation.reasoning
        },
        "demo_time": datetime.now().isoformat()
    }
    
    # 保存到文件
    with open("demo_results.json", "w", encoding="utf-8") as f:
        json.dump(demo_results, f, ensure_ascii=False, indent=2)
    
    print(f"📄 演示结果已保存到: demo_results.json")


if __name__ == "__main__":
    print("启动个性化学习路径推荐系统演示...")
    print()
    try:
        asyncio.run(demo_complete_learning_journey())
    except Exception as e:
        print(f"❌ 演示运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
