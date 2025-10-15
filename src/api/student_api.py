"""学生信息API接口"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional

from ..services.student_service import get_student_service
from ..middleware.auth_middleware import security, verify_token

logger = logging.getLogger(__name__)

# 创建路由器
student_router = APIRouter(prefix="/api/student", tags=["学生信息"])


@student_router.get("/profile", summary="获取学生档案")
async def get_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取学生完整档案
    
    包含基本信息和学习统计
    """
    try:
        # 验证Token
        student_id = await verify_token(credentials)
        
        student_service = get_student_service()
        profile = student_service.get_student_profile(student_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="学生信息不存在")
        
        return JSONResponse(content=profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学生档案失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@student_router.get("/diagnostic-history", summary="获取诊断历史")
async def get_diagnostic_history(
    limit: Optional[int] = Query(10, ge=1, le=100, description="返回记录数量"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取学生的诊断测试历史记录
    
    按时间倒序返回
    """
    try:
        # 验证Token
        student_id = await verify_token(credentials)
        
        student_service = get_student_service()
        history = student_service.get_diagnostic_history(student_id, limit=limit)
        
        return JSONResponse(
            content={
                "count": len(history),
                "history": history
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取诊断历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@student_router.get("/latest-diagnostic", summary="获取最新诊断")
async def get_latest_diagnostic(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取学生最新的诊断测试结果
    """
    try:
        # 验证Token
        student_id = await verify_token(credentials)
        
        student_service = get_student_service()
        latest = student_service.get_latest_diagnostic(student_id)
        
        if not latest:
            return JSONResponse(
                content={
                    "has_diagnostic": False,
                    "message": "尚未完成诊断测试"
                }
            )
        
        return JSONResponse(
            content={
                "has_diagnostic": True,
                "diagnostic": latest
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新诊断失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@student_router.get("/learning-history", summary="获取学习历史")
async def get_learning_history(
    limit: int = Query(50, ge=1, le=200, description="返回记录数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取学生的学习历史记录
    
    包含所有作业评估记录
    """
    try:
        # 验证Token
        student_id = await verify_token(credentials)
        
        student_service = get_student_service()
        result = student_service.get_learning_history(
            student_id, 
            limit=limit, 
            offset=offset
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@student_router.get("/statistics", summary="获取学习统计")
async def get_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取学生的学习统计信息
    
    包含诊断次数、作业数量、平均分等
    """
    try:
        # 验证Token
        student_id = await verify_token(credentials)
        
        student_service = get_student_service()
        stats = student_service.get_learning_statistics(student_id)
        
        return JSONResponse(content=stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@student_router.get("/learning-path", summary="获取学习路径")
async def get_learning_path(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取学生当前的学习路径信息
    
    包含当前节点、进度、推荐等
    """
    try:
        # 验证Token
        student_id = await verify_token(credentials)
        
        # 从学习路径服务获取数据
        from ..services.learning_path_service import LearningPathService
        path_service = LearningPathService()
        
        try:
            progress = path_service.get_student_progress(student_id)
            
            if not progress:
                return JSONResponse(
                    content={
                        "has_path": False,
                        "message": "尚未初始化学习路径，请先完成诊断测试"
                    }
                )
            
            # 获取推荐
            recommendation = await path_service.recommend_next_step(student_id)
            
            return JSONResponse(
                content={
                    "has_path": True,
                    "current_channel": progress.current_channel.value,
                    "current_node": progress.current_node_id,
                    "completed_nodes": list(progress.completed_nodes),
                    "progress_percentage": len(progress.completed_nodes) * 100 / 23 if progress.completed_nodes else 0,  # 假设总共23个节点
                    "recommendations": {
                        "next_node": recommendation.next_node_id,
                        "decision_type": recommendation.decision.value,
                        "reasoning": recommendation.reasoning,
                        "estimated_time": recommendation.estimated_completion_time
                    } if recommendation else None
                }
            )
            
        except Exception as e:
            logger.warning(f"获取学习路径失败: {str(e)}")
            return JSONResponse(
                content={
                    "has_path": False,
                    "message": "学习路径数据不可用"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
