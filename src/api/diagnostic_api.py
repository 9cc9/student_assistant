"""诊断测试API接口"""

from fastapi import HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime

from ..services.diagnostic_service import DiagnosticService, DiagnosticServiceError
from ..services.student_service import get_student_service
from ..models.student_auth import DiagnosticRecord

logger = logging.getLogger(__name__)

# 初始化诊断服务
diagnostic_service = DiagnosticService()


async def get_diagnostic_test() -> JSONResponse:
    """
    获取入学诊断测试题目
    
    返回包含概念测试、编程测试、工具调查和学习偏好调查的完整测试
    """
    try:
        logger.info("🧪 获取诊断测试题目")
        
        test_data = diagnostic_service.get_diagnostic_test()
        
        response_data = {
            "test_info": test_data["test_info"],
            "sections": test_data["sections"],
            "total_estimated_time": sum(
                section.get("time_limit", 0) for section in test_data["sections"]
            ),
            "instructions": [
                "请认真完成所有测试题目，这将帮助我们为你推荐最合适的学习路径",
                "测试不计入成绩，请如实回答",
                "预计需要10-15分钟完成",
                "你可以在任何时候暂停和继续测试"
            ],
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info("🧪 ✅ 诊断测试题目获取成功")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"🧪 ❌ 获取诊断测试失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取诊断测试失败: {str(e)}"
        )


async def submit_diagnostic_test(
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "student_id": "s_20250101",
            "responses": {
                "concepts": {
                    "concept_1": "A",
                    "concept_2": "A",
                    "concept_3": "B",
                    "concept_4": "B",
                    "concept_5": "前端负责用户界面，后端负责数据处理"
                },
                "coding": {
                    "code_1": "def find_max(numbers):\n    return max(numbers)",
                    "code_2": "import requests\n\ndef fetch_data(url):\n    try:\n        response = requests.get(url)\n        response.raise_for_status()\n        return response.json()\n    except Exception as e:\n        return None",
                    "code_3": "x会输出[1, 2, 3, 4]因为列表是引用类型"
                },
                "tools": {
                    "Python": 4,
                    "JavaScript": 3,
                    "Git": 2,
                    "命令行/Terminal": 3,
                    "HTML/CSS": 4,
                    "React/Vue": 2,
                    "Node.js": 2,
                    "REST API": 3,
                    "OpenAI API": 2,
                    "LangChain": 1,
                    "向量数据库": 1,
                    "Jupyter Notebook": 3,
                    "Docker": 2,
                    "云服务": 1,
                    "Linux": 2,
                    "数据库": 3
                },
                "preferences": {
                    "learning_style": "examples_first",
                    "time_budget": 6,
                    "interests": ["RAG", "Web开发"],
                    "goals": ["完成RAG应用", "掌握全栈开发"],
                    "challenges": "debugging"
                }
            }
        }
    )
) -> JSONResponse:
    """
    提交诊断测试答案，生成学生画像
    
    评估学生的回答，生成个性化学习画像，并推荐初始学习路径
    """
    try:
        student_id = request_data.get("student_id")
        student_responses = request_data.get("responses", {})
        
        if not student_id:
            raise HTTPException(status_code=400, detail="缺少学生ID")
        
        if not student_responses:
            raise HTTPException(status_code=400, detail="缺少测试答案")
        
        logger.info(f"🧪 处理诊断测试提交: {student_id}")
        
        # 评估诊断结果
        evaluation_results = diagnostic_service.evaluate_diagnostic_results(student_responses)
        
        # 确定学习水平
        overall_readiness = evaluation_results["overall_readiness"]
        avg_score = (
            evaluation_results["concept_score"] + 
            evaluation_results["coding_score"] + 
            evaluation_results["tool_familiarity"]
        ) / 3
        
        # 映射学习水平
        if avg_score >= 85:
            level = "L3"  # 高级/竞赛型
        elif avg_score >= 70:
            level = "L2"  # 中级
        elif avg_score >= 50:
            level = "L1"  # 初级
        else:
            level = "L0"  # 零基础
        
        # 识别薄弱技能
        weak_skills = []
        for skill, score in evaluation_results["skill_scores"].items():
            if score < 60:
                weak_skills.append(skill)
        
        # 添加基于测试表现的薄弱技能
        if evaluation_results["concept_score"] < 60:
            weak_skills.append("技术概念理解")
        if evaluation_results["coding_score"] < 60:
            weak_skills.append("编程基础")
        
        # 构建学生画像
        student_profile = {
            "student_id": student_id,
            "level": level,
            "weak_skills": weak_skills[:5],  # 最多5个
            "interests": evaluation_results["interests"],
            "learning_style": evaluation_results["learning_style_preference"],
            "time_budget_hours_per_week": evaluation_results["time_budget_hours_per_week"],
            "goals": evaluation_results["goals"]
        }
        
        # 生成推荐起始通道
        if level == "L0":
            recommended_channel = "A"
            channel_description = "基础保底通道 - 注重基础夯实，循序渐进"
        elif level == "L1":
            recommended_channel = "B"
            channel_description = "标准实践通道 - 平衡理论与实践"
        elif level == "L2":
            recommended_channel = "B"
            channel_description = "标准实践通道 - 可尝试部分C通道挑战"
        else:  # L3
            recommended_channel = "C"
            channel_description = "挑战拓展通道 - 追求工程化和高阶技能"
        
        # 保存诊断记录到学生历史
        test_id = f"test_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        diagnostic_record = DiagnosticRecord(
            student_id=student_id,
            test_id=test_id,
            submitted_at=datetime.now(),
            concept_score=int(evaluation_results["concept_score"]),
            coding_score=int(evaluation_results["coding_score"]),
            tool_familiarity=int(evaluation_results["tool_familiarity"]),
            overall_readiness=overall_readiness,
            learning_level=level,
            learning_style=evaluation_results["learning_style_preference"],
            interests=evaluation_results["interests"]
        )
        
        student_service = get_student_service()
        student_service.save_diagnostic_record(diagnostic_record)
        
        response_data = {
            "student_id": student_id,
            "test_id": test_id,
            "evaluation_completed": True,
            "evaluation_results": {
                "concept_score": evaluation_results["concept_score"],
                "coding_score": evaluation_results["coding_score"],
                "tool_familiarity": evaluation_results["tool_familiarity"],
                "overall_readiness": overall_readiness,
                "overall_readiness_description": _get_readiness_description(overall_readiness)
            },
            "student_profile": student_profile,
            "recommendations": {
                "recommended_channel": recommended_channel,
                "channel_description": channel_description,
                "learning_suggestions": evaluation_results["recommendations"],
                "focus_areas": weak_skills[:3] if weak_skills else ["全面提升各项技能"],
                "estimated_weekly_progress": _estimate_weekly_progress(
                    level, 
                    evaluation_results["time_budget_hours_per_week"]
                )
            },
            "next_steps": [
                f"你的水平评定为 {level} - {_get_level_description(level)}",
                f"推荐从 {recommended_channel} 通道开始学习",
                "系统已为你生成个性化学习路径",
                "点击开始学习即可进入第一个学习节点"
            ],
            "evaluated_at": evaluation_results["evaluated_at"]
        }
        
        logger.info(f"🧪 ✅ 诊断测试评估完成并保存: {student_id}, 水平: {level}")
        return JSONResponse(content=response_data, status_code=200)
        
    except DiagnosticServiceError as e:
        logger.error(f"🧪 ❌ 诊断服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"诊断服务错误: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🧪 ❌ 提交诊断测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交诊断测试失败: {str(e)}")


def _get_readiness_description(readiness: str) -> str:
    """获取准备度描述"""
    descriptions = {
        "优秀": "你的基础非常扎实，可以尝试更多挑战性任务",
        "良好": "你已经具备较好的基础，适合标准学习路径",
        "合格": "你具备基本的学习能力，建议从基础开始稳扎稳打",
        "需要加强": "建议先加强基础知识，系统会为你提供额外支持"
    }
    return descriptions.get(readiness, "继续努力学习")


def _get_level_description(level: str) -> str:
    """获取水平描述"""
    descriptions = {
        "L0": "入门新手，适合从基础开始",
        "L1": "初级水平，掌握基本概念",
        "L2": "中级水平，可以独立完成项目",
        "L3": "高级水平，适合挑战性任务和竞赛"
    }
    return descriptions.get(level, "")


def _estimate_weekly_progress(level: str, time_budget: int) -> str:
    """估算每周学习进度"""
    base_hours = {
        "L0": 8,   # 基础学生需要更多时间
        "L1": 6,   # 初级学生标准时间
        "L2": 5,   # 中级学生效率更高
        "L3": 4    # 高级学生最高效
    }
    
    required_hours = base_hours.get(level, 6)
    
    if time_budget >= required_hours * 1.5:
        return "快速进度 - 预计可以提前完成"
    elif time_budget >= required_hours:
        return "标准进度 - 按计划稳步推进"
    else:
        return "舒适进度 - 建议适当延长学习周期"


async def get_diagnostic_statistics() -> JSONResponse:
    """
    获取诊断测试统计信息
    
    返回诊断测试的统计数据，用于系统分析
    """
    try:
        logger.info("🧪 查询诊断统计信息")
        
        # 这里可以从数据库获取统计数据
        # 目前返回模拟数据结构
        stats = {
            "total_tests_completed": 0,
            "average_scores": {
                "concept": 0,
                "coding": 0,
                "tool_familiarity": 0
            },
            "level_distribution": {
                "L0": 0,
                "L1": 0,
                "L2": 0,
                "L3": 0
            },
            "common_weak_skills": [],
            "popular_interests": []
        }
        
        response_data = {
            "statistics": stats,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info("🧪 ✅ 诊断统计信息查询成功")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"🧪 ❌ 查询诊断统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查询诊断统计信息失败: {str(e)}"
        )

