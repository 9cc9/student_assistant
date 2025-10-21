"""学习路径管理API接口"""

from fastapi import HTTPException, Body, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..services.learning_path_service import LearningPathService, LearningPathServiceError
from ..services.path_recommendation_engine import PathRecommendationEngine, PathRecommendationEngineError
from ..models.learning_path import Channel, NodeStatus
from ..models.student import StudentProfile, LearningLevel, LearningStyle

logger = logging.getLogger(__name__)

# 初始化服务
path_service = LearningPathService()
recommendation_engine = PathRecommendationEngine()


async def submit_diagnostic_assessment(
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "student_id": "s_20250101",
            "diagnostic_results": {
                "concept_score": 75,
                "coding_score": 68,
                "tool_familiarity": 80,
                "skill_scores": {
                    "Python基础": 70,
                    "Git": 45,
                    "HTTP协议": 65,
                    "调试技能": 50
                },
                "interests": ["RAG", "Agent", "移动端"],
                "learning_style_preference": "examples_first",
                "time_budget_hours_per_week": 8,
                "goals": ["完成RAG应用", "掌握全栈开发"]
            }
        }
    )
) -> JSONResponse:
    """
    提交入学诊断评估，生成学生画像和初始学习路径
    
    这个接口是学生开始学习的第一步，通过入学诊断结果：
    1. 生成个性化学生画像
    2. 初始化学习路径进度
    3. 推荐初始学习策略
    """
    try:
        student_id = request_data.get("student_id")
        diagnostic_results = request_data.get("diagnostic_results", {})
        
        if not student_id:
            raise HTTPException(status_code=400, detail="缺少学生ID")
        
        logger.info(f"📚 开始处理入学诊断: {student_id}")
        
        # 创建学生画像
        student_profile = await path_service.create_student_profile(
            student_id, diagnostic_results
        )
        
        # 初始化学习路径进度
        progress = await path_service.initialize_student_path(student_id, student_profile)
        
        # 生成初始路径推荐
        initial_recommendation = await recommendation_engine.recommend_initial_path(
            student_profile, diagnostic_results
        )
        
        response_data = {
            "student_id": student_id,
            "profile_created": True,
            "student_profile": {
                "level": student_profile.level.value,
                "weak_skills": student_profile.weak_skills,
                "interests": student_profile.interests,
                "learning_style": student_profile.learning_style.value,
                "time_budget": student_profile.time_budget_hours_per_week,
                "goals": student_profile.goals
            },
            "initial_path": {
                "current_node": progress.current_node_id,
                "recommended_channel": progress.current_channel.value,
                "available_nodes": list(progress.node_statuses.keys()),
                "estimated_timeline": initial_recommendation["estimated_timeline"]
            },
            "recommendations": initial_recommendation,
            "next_steps": [
                f"开始 {progress.current_node_id} 节点的 {progress.current_channel.value} 通道学习",
                "查看推荐的学习资源和策略",
                "按照个性化时间安排进行学习"
            ],
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"📚 ✅ 入学诊断处理完成: {student_id}")
        return JSONResponse(content=response_data, status_code=201)
        
    except LearningPathServiceError as e:
        logger.error(f"📚 ❌ 学习路径服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"学习路径服务错误: {str(e)}")
    except PathRecommendationEngineError as e:
        logger.error(f"📚 ❌ 推荐引擎错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"推荐引擎错误: {str(e)}")
    except Exception as e:
        logger.error(f"📚 ❌ 处理入学诊断失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理入学诊断失败: {str(e)}")


async def get_student_progress(student_id: str) -> JSONResponse:
    """
    获取学生学习进度
    
    返回学生当前的学习状态、完成情况和下一步建议
    """
    try:
        logger.info(f"📚 收到学习进度查询请求: student_id={student_id}")
        
        progress = path_service.get_student_progress(student_id)
        if not progress:
            error_msg = f"学生学习进度不存在: {student_id}"
            logger.error(f"📚 ❌ {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        logger.info(f"📚 学生进度查询成功: 当前节点={progress.current_node_id}, 当前通道={progress.current_channel.value}")
        
        # 获取学习路径信息
        learning_path = path_service.get_learning_path()
        if not learning_path:
            raise HTTPException(status_code=500, detail="默认学习路径不存在")
        
        # 构建当前节点信息
        current_node = None
        for node in learning_path.nodes:
            if node.id == progress.current_node_id:
                current_node = node
                break
        
        response_data = {
            "student_id": student_id,
            "current_status": {
                "current_node_id": progress.current_node_id,
                "current_node_name": current_node.name if current_node else "未知节点",
                "current_channel": progress.current_channel.value,
                "node_status": progress.node_statuses.get(progress.current_node_id, "unknown")
            },
            "progress_summary": {
                "completed_nodes": progress.completed_nodes,
                "completed_channels": progress.completed_channels,
                "total_nodes": len(learning_path.nodes),
                "completion_rate": len(progress.completed_nodes) / len(learning_path.nodes),
                "total_study_hours": progress.total_study_hours
            },
            "performance_data": {
                "mastery_scores": progress.mastery_scores,
                "frustration_level": progress.frustration_level,
                "retry_counts": progress.retry_counts
            },
            "current_task": _get_current_task_info(current_node, progress.current_channel) if current_node else None,
            "next_milestone": _get_next_milestone(learning_path.nodes, progress),
            "last_activity": progress.last_activity_at.isoformat(),
            "started_at": progress.started_at.isoformat()
        }
        
        logger.info(f"📚 ✅ 学生进度查询成功: {student_id}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"📚 ❌ 查询学生进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询学生进度失败: {str(e)}")


def _get_current_task_info(current_node, current_channel: Channel) -> Dict[str, Any]:
    """获取当前任务信息"""
    channel_task = current_node.channel_tasks.get(current_channel, {})
    
    return {
        "node_name": current_node.name,
        "channel": current_channel.value,
        "task_description": channel_task.get("task", ""),
        "requirements": channel_task.get("requirements", []),
        "deliverables": channel_task.get("deliverables", []),
        "estimated_hours": current_node.estimated_hours.get(current_channel, 0),
        "difficulty_level": current_node.difficulty_level.get(current_channel, 0),
        "checkpoint": {
            "must_pass": current_node.checkpoint.must_pass if current_node.checkpoint else [],
            "evidence_required": current_node.checkpoint.evidence if current_node.checkpoint else []
        }
    }


def _get_next_milestone(nodes, progress) -> Optional[Dict[str, Any]]:
    """获取下一个里程碑"""
    node_sequence = ["api_calling", "model_deployment", "no_code_ai", "rag_system", "ui_design", "frontend_dev", "backend_dev"]
    
    try:
        current_index = node_sequence.index(progress.current_node_id)
        if current_index < len(node_sequence) - 1:
            next_node_id = node_sequence[current_index + 1]
            next_node = next((node for node in nodes if node.id == next_node_id), None)
            
            if next_node:
                return {
                    "node_id": next_node.id,
                    "node_name": next_node.name,
                    "description": next_node.description,
                    "prerequisites": next_node.prerequisites,
                    "estimated_unlock": "完成当前节点后解锁"
                }
    except ValueError:
        pass
    
    return None


async def request_path_recommendation(
    student_id: str,
    include_assessment: bool = Query(False, description="是否包含最新评估结果")
) -> JSONResponse:
    """
    请求学习路径推荐
    
    基于学生当前进度和历史表现，生成个性化的路径调整建议
    """
    try:
        logger.info(f"📚 生成路径推荐: {student_id}")
        
        progress = path_service.get_student_progress(student_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"学生学习进度不存在: {student_id}")
        
        # 如果需要包含评估结果，这里可以获取最新的评估数据
        assessment_result = None
        if include_assessment:
            # TODO: 从评估服务获取最新评估结果
            pass
        
        # 生成推荐
        recommendation = await path_service.recommend_next_step(student_id, assessment_result)
        
        response_data = {
            "student_id": student_id,
            "recommendation": {
                "recommended_channel": recommendation.recommended_channel.value,
                "next_node_id": recommendation.next_node_id,
                "decision_type": recommendation.decision.value,
                "reasoning": recommendation.reasoning,
                "estimated_completion_time": recommendation.estimated_completion_time
            },
            "trigger_factors": recommendation.trigger_factors,
            "alternative_options": recommendation.alternative_options,
            "scaffold_resources": recommendation.scaffold_resources,
            "implementation_steps": [
                f"调整到 {recommendation.recommended_channel.value} 通道",
                f"开始 {recommendation.next_node_id} 节点学习",
                "关注推荐的脚手架资源",
                f"预计需要 {recommendation.estimated_completion_time} 小时完成"
            ],
            "created_at": recommendation.created_at.isoformat()
        }
        
        logger.info(f"📚 ✅ 路径推荐生成成功: {student_id}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"📚 ❌ 生成路径推荐失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成路径推荐失败: {str(e)}")


async def update_node_progress(
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "student_id": "s_20250101",
            "node_id": "api_calling",
            "status": "completed",
            "assessment_result": {
                "overall_score": 85,
                "breakdown": {"idea": 80, "ui": 90, "code": 85}
            }
        }
    )
) -> JSONResponse:
    """
    更新节点学习进度
    
    当学生完成某个节点的学习或提交作业时，更新进度状态。
    这个接口会被AI助教系统在评估完成后自动调用。
    """
    try:
        student_id = request_data.get("student_id")
        node_id = request_data.get("node_id")
        status_str = request_data.get("status")
        assessment_result = request_data.get("assessment_result")
        
        if not all([student_id, node_id, status_str]):
            raise HTTPException(status_code=400, detail="缺少必要参数: student_id, node_id, status")
        
        # 转换状态枚举
        try:
            status = NodeStatus(status_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的节点状态: {status_str}")
        
        logger.info(f"📚 更新节点进度: {student_id} -> {node_id} -> {status.value}")
        
        # 更新进度
        await path_service.update_student_progress(student_id, node_id, status, assessment_result)
        
        # 如果节点完成且有评估结果，生成新的路径推荐
        recommendation = None
        if status == NodeStatus.COMPLETED and assessment_result:
            try:
                recommendation = await path_service.recommend_next_step(student_id, assessment_result)
            except Exception as e:
                logger.warning(f"📚 ⚠️ 生成路径推荐失败，但进度更新成功: {str(e)}")
        
        # 获取更新后的进度
        updated_progress = path_service.get_student_progress(student_id)
        
        response_data = {
            "student_id": student_id,
            "node_id": node_id,
            "status": status.value,
            "update_successful": True,
            "current_progress": {
                "current_node": updated_progress.current_node_id,
                "current_channel": updated_progress.current_channel.value,
                "completed_nodes": updated_progress.completed_nodes,
                "completion_rate": len(updated_progress.completed_nodes) / 7  # 7个总节点
            }
        }
        
        # 如果有推荐，添加到响应中
        if recommendation:
            response_data["path_recommendation"] = {
                "recommended_channel": recommendation.recommended_channel.value,
                "next_node_id": recommendation.next_node_id,
                "decision_type": recommendation.decision.value,
                "reasoning": recommendation.reasoning
            }
        
        logger.info(f"📚 ✅ 节点进度更新成功: {student_id}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except LearningPathServiceError as e:
        logger.error(f"📚 ❌ 更新节点进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"📚 ❌ 更新节点进度异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新节点进度失败: {str(e)}")


async def get_learning_path_info() -> JSONResponse:
    """
    获取学习路径信息
    
    返回课程的完整学习路径，包括所有节点和通道设置
    """
    try:
        logger.info("📚 查询学习路径信息")
        
        learning_path = path_service.get_learning_path()
        if not learning_path:
            raise HTTPException(status_code=500, detail="默认学习路径不存在")
        
        # 构建路径信息
        nodes_info = []
        for node in learning_path.nodes:
            node_info = {
                "id": node.id,
                "name": node.name,
                "description": node.description,
                "order": node.order,
                "prerequisites": node.prerequisites,
                "channels": {
                    "A": {
                        "task": node.channel_tasks[Channel.A]["task"],
                        "requirements": node.channel_tasks[Channel.A]["requirements"],
                        "estimated_hours": node.estimated_hours[Channel.A],
                        "difficulty": node.difficulty_level[Channel.A]
                    },
                    "B": {
                        "task": node.channel_tasks[Channel.B]["task"],
                        "requirements": node.channel_tasks[Channel.B]["requirements"],
                        "estimated_hours": node.estimated_hours[Channel.B],
                        "difficulty": node.difficulty_level[Channel.B]
                    },
                    "C": {
                        "task": node.channel_tasks[Channel.C]["task"],
                        "requirements": node.channel_tasks[Channel.C]["requirements"],
                        "estimated_hours": node.estimated_hours[Channel.C],
                        "difficulty": node.difficulty_level[Channel.C]
                    }
                },
                "checkpoint": {
                    "id": node.checkpoint.checkpoint_id if node.checkpoint else None,
                    "requirements": node.checkpoint.must_pass if node.checkpoint else [],
                    "evidence": node.checkpoint.evidence if node.checkpoint else [],
                    "auto_grade_rules": node.checkpoint.auto_grade if node.checkpoint else {}
                } if node.checkpoint else None,
                "remedy_resources": node.remedy_resources
            }
            nodes_info.append(node_info)
        
        response_data = {
            "path_info": {
                "id": learning_path.id,
                "name": learning_path.name,
                "description": learning_path.description,
                "total_nodes": len(learning_path.nodes),
                "default_channel": learning_path.default_channel.value,
                "upgrade_threshold": learning_path.upgrade_threshold,
                "downgrade_threshold": learning_path.downgrade_threshold,
                "max_retries": learning_path.max_retries
            },
            "nodes": nodes_info,
            "path_config": {
                "target_audience": learning_path.target_audience,
                "prerequisites_knowledge": learning_path.prerequisites_knowledge,
                "learning_outcomes": learning_path.learning_outcomes
            },
            "channel_descriptions": {
                "A": "基础保底通道 - 注重基础概念掌握和实践入门",
                "B": "标准实践通道 - 涵盖主流技能和完整项目体验",
                "C": "挑战拓展通道 - 追求工程化实践和高阶技能"
            }
        }
        
        logger.info("📚 ✅ 学习路径信息查询成功")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"📚 ❌ 查询学习路径信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询学习路径信息失败: {str(e)}")


async def get_available_paths() -> JSONResponse:
    """
    获取所有可用的学习路径
    
    返回系统中所有可用的学习路径概要信息
    """
    try:
        logger.info("📚 查询可用学习路径")
        
        paths = path_service.get_available_paths()
        
        response_data = {
            "available_paths": paths,
            "total_paths": len(paths),
            "default_path": "default_course_path"
        }
        
        logger.info(f"📚 ✅ 查询到 {len(paths)} 个可用学习路径")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"📚 ❌ 查询可用学习路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询可用学习路径失败: {str(e)}")


async def get_path_statistics() -> JSONResponse:
    """
    获取学习路径统计信息
    
    返回系统的整体学习统计数据，用于管理和分析
    """
    try:
        logger.info("📚 查询路径统计信息")
        
        # 获取学生进度统计
        all_progresses = list(path_service.student_progresses.values())
        
        if not all_progresses:
            stats = {
                "total_students": 0,
                "active_students": 0,
                "completion_stats": {},
                "channel_distribution": {},
                "average_progress": 0
            }
        else:
            # 统计完成率
            completion_stats = {}
            for progress in all_progresses:
                completion_rate = len(progress.completed_nodes) / 7  # 7个总节点
                rate_range = f"{int(completion_rate * 100 // 10) * 10}-{int(completion_rate * 100 // 10) * 10 + 10}%"
                completion_stats[rate_range] = completion_stats.get(rate_range, 0) + 1
            
            # 统计通道分布
            channel_distribution = {}
            for progress in all_progresses:
                channel = progress.current_channel.value
                channel_distribution[channel] = channel_distribution.get(channel, 0) + 1
            
            # 计算平均进度
            total_completion = sum(len(p.completed_nodes) for p in all_progresses)
            average_progress = total_completion / len(all_progresses) if all_progresses else 0
            
            stats = {
                "total_students": len(all_progresses),
                "active_students": len([p for p in all_progresses 
                                     if (datetime.now() - p.last_activity_at).days <= 7]),
                "completion_stats": completion_stats,
                "channel_distribution": channel_distribution,
                "average_progress": round(average_progress, 2),
                "average_completion_rate": round(average_progress / 7 * 100, 1)
            }
        
        response_data = {
            "statistics": stats,
            "system_info": {
                "total_paths": len(path_service.learning_paths),
                "total_nodes": 7,
                "available_channels": ["A", "B", "C"]
            },
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info("📚 ✅ 路径统计信息查询成功")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"📚 ❌ 查询路径统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询路径统计信息失败: {str(e)}")


# 用于健康检查的简单接口
async def switch_student_channel(
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "student_id": "s_20250101",
            "node_id": "api_calling",
            "channel": "C"
        }
    )
) -> JSONResponse:
    """
    切换学生学习通道
    
    允许学生在当前学习节点切换A/B/C通道的难度等级
    """
    try:
        # 详细记录接收到的请求数据
        logger.info(f"📚 收到通道切换请求: {request_data}")
        
        student_id = request_data.get("student_id")
        node_id = request_data.get("node_id")
        channel_str = request_data.get("channel")
        
        # 记录解析后的参数
        logger.info(f"📚 解析参数 - student_id: {student_id}, node_id: {node_id}, channel: {channel_str}")
        
        # 检查必要参数
        missing_params = []
        if not student_id:
            missing_params.append("student_id")
        if not node_id:
            missing_params.append("node_id")
        if not channel_str:
            missing_params.append("channel")
            
        if missing_params:
            error_msg = f"缺少必要参数: {', '.join(missing_params)}"
            logger.error(f"📚 ❌ 参数验证失败: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 验证通道值
        try:
            channel = Channel(channel_str)
            logger.info(f"📚 通道值验证成功: {channel_str} -> {channel.value}")
        except ValueError as e:
            error_msg = f"无效的通道值: {channel_str}，有效值为: A, B, C"
            logger.error(f"📚 ❌ 通道值验证失败: {error_msg}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"📚 开始切换学生通道: {student_id} -> {node_id} -> {channel.value}")
        
        # 获取学生进度
        logger.info(f"📚 查询学生学习进度: {student_id}")
        progress = path_service.get_student_progress(student_id)
        if not progress:
            error_msg = f"学生学习进度不存在: {student_id}"
            logger.error(f"📚 ❌ {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        logger.info(f"📚 学生进度查询成功: 当前节点={progress.current_node_id}, 当前通道={progress.current_channel.value}")
        
        # 验证是否为当前节点
        if progress.current_node_id != node_id:
            error_msg = f"只能切换当前学习节点({progress.current_node_id})的通道，请求的节点: {node_id}"
            logger.error(f"📚 ❌ 节点验证失败: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 切换通道
        logger.info(f"📚 开始更新学生通道: {progress.current_channel.value} -> {channel.value}")
        progress.current_channel = channel
        progress.last_activity_at = datetime.now()
        progress.updated_at = datetime.now()
        
        # 保存更新到数据库
        logger.info(f"📚 保存学生进度更新到数据库")
        from src.services.progress_repository import ProgressRepository
        ProgressRepository.update_student_progress(progress)
        
        # 获取更新后的任务信息
        logger.info(f"📚 获取更新后的任务信息")
        learning_path = path_service.get_learning_path()
        current_node = None
        for node in learning_path.nodes:
            if node.id == node_id:
                current_node = node
                break
        
        if not current_node:
            logger.warning(f"📚 ⚠️ 未找到节点信息: {node_id}")
        
        current_task = _get_current_task_info(current_node, channel) if current_node else None
        
        response_data = {
            "student_id": student_id,
            "node_id": node_id,
            "channel": channel.value,
            "switch_successful": True,
            "current_task": current_task,
            "updated_at": progress.updated_at.isoformat()
        }
        
        logger.info(f"📚 ✅ 学生通道切换成功: {student_id} -> {channel.value}")
        logger.info(f"📚 响应数据: {response_data}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except LearningPathServiceError as e:
        logger.error(f"📚 ❌ 切换通道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"📚 ❌ 切换通道异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"切换通道失败: {str(e)}")


async def clear_student_progress(student_id: str) -> JSONResponse:
    """
    清除学生学习进度（用于重新开始学习）
    
    这个接口会删除学生的所有学习进度数据，包括：
    - 全局学习进度
    - 所有节点的学习状态
    - 掌握度分数
    - 重试次数等
    
    注意：此操作不可逆，请谨慎使用！
    """
    try:
        logger.info(f"📚 开始清除学生学习进度: {student_id}")
        
        # 清除学习进度
        cleared = await path_service.clear_student_progress(student_id)
        
        if not cleared:
            return JSONResponse(
                content={
                    "student_id": student_id,
                    "cleared": False,
                    "message": "学生没有学习进度，无需清除"
                },
                status_code=200
            )
        
        response_data = {
            "student_id": student_id,
            "cleared": True,
            "message": "学习进度已成功清除，可以重新开始学习",
            "cleared_at": datetime.now().isoformat()
        }
        
        logger.info(f"📚 ✅ 学生学习进度清除成功: {student_id}")
        return JSONResponse(content=response_data)
        
    except LearningPathServiceError as e:
        logger.error(f"📚 ❌ 清除学习进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"📚 ❌ 清除学习进度异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除学习进度失败: {str(e)}")


async def learning_path_health_check() -> JSONResponse:
    """学习路径系统健康检查"""
    try:
        # 检查服务是否正常
        path_count = len(path_service.learning_paths)
        student_count = len(path_service.student_progresses)
        
        return JSONResponse(content={
            "status": "healthy",
            "service": "learning_path_system",
            "paths_loaded": path_count,
            "active_students": student_count,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"📚 ❌ 健康检查失败: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )
