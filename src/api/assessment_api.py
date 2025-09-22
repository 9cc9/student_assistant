"""评估系统API接口"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

from ..services.gateway_service import GatewayService, GatewayError


# 数据模型定义
class DeliverableData(BaseModel):
    """提交物数据模型"""
    idea_text: str = Field(..., description="创意描述文本")
    ui_images: List[str] = Field(default=[], description="UI设计图片列表（base64编码）")
    code_repo: Optional[str] = Field(None, description="代码仓库链接")
    code_snippets: List[str] = Field(default=[], description="代码片段列表")


class AssessmentRequest(BaseModel):
    """评估请求模型"""
    student_id: str = Field(..., description="学生ID")
    deliverables: DeliverableData = Field(..., description="提交物数据")


class BatchAssessmentRequest(BaseModel):
    """批量评估请求模型"""
    requests: List[AssessmentRequest] = Field(..., description="评估请求列表")


class AssessmentResponse(BaseModel):
    """评估响应模型"""
    assessment_id: str
    status: str
    message: Optional[str] = None


class SyncRequest(BaseModel):
    """同步请求模型"""
    assessment_id: str = Field(..., description="评估ID")


# 初始化服务
gateway_service = GatewayService()
logger = logging.getLogger(__name__)


async def submit_assessment(request: AssessmentRequest) -> AssessmentResponse:
    """
    提交评估请求
    
    接收学生提交的作品（Idea说明、设计图/原型、代码仓库或片段），
    启动并行评估流程，返回评估ID用于后续查询结果。
    """
    try:
        request_data = {
            "student_id": request.student_id,
            "deliverables": request.deliverables.dict()
        }
        
        result = await gateway_service.submit_for_assessment(request_data)
        
        return AssessmentResponse(
            assessment_id=result["assessment_id"],
            status=result["status"],
            message=result.get("message")
        )
        
    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"提交评估请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器，将作为普通函数导出
async def get_assessment_result(assessment_id: str):
    """
    获取评估结果
    
    根据评估ID查询评估状态和结果，包括：
    - 总体评分和各维度得分
    - 诊断信息和改进建议
    - 推荐学习资源
    - 准出规则和路径更新建议
    """
    try:
        result = await gateway_service.get_assessment_result(assessment_id)
        return result
        
    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取评估结果失败: {assessment_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器
async def export_path_rules(request: SyncRequest):
    """
    导出准出规则到学习路径引擎
    
    将评估结果转换为准出规则，同步到学习路径引擎，
    用于决定学生的学习路径调整（升级/保持/降级/回流）。
    """
    try:
        result = await gateway_service.sync_to_path_engine(request.assessment_id)
        return result
        
    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"导出准出规则失败: {request.assessment_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器
async def batch_submit_assessments(request: BatchAssessmentRequest):
    """
    批量提交评估请求
    
    支持一次性提交多个学生的评估请求，
    适用于班级统一作业评估场景。
    """
    try:
        requests_data = []
        for req in request.requests:
            requests_data.append({
                "student_id": req.student_id,
                "deliverables": req.deliverables.dict()
            })
        
        results = await gateway_service.batch_submit_assessments(requests_data)
        return {"results": results}
        
    except Exception as e:
        logger.error(f"批量提交评估失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器
async def get_assessment_history(
    student_id: Optional[str] = None,
    limit: int = 50
):
    """
    获取评估历史记录
    
    查询历史评估记录，支持按学生ID过滤，
    用于学习进度跟踪和历史成绩查看。
    """
    try:
        history = gateway_service.get_assessment_history(student_id, limit)
        return {"assessments": history}
        
    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取评估历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器
async def get_system_status():
    """
    获取系统状态
    
    返回评估系统的运行状态，包括：
    - 当前活跃评估数量
    - 系统负载情况
    - 服务健康状态
    """
    try:
        status_info = gateway_service.get_system_status()
        return status_info
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器
async def get_system_statistics(days: int = 7):
    """
    获取系统统计信息
    
    返回指定时间段内的评估统计数据，包括：
    - 评估总数和完成率
    - 平均分数和分布情况
    - 系统性能指标
    """
    try:
        statistics = gateway_service.get_statistics(days)
        return statistics
        
    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内部服务器错误"
        )


# 移除装饰器
async def root():
    """根路径，返回API信息"""
    return {
        "service": "AI助教评估系统",
        "version": "1.0.0",
        "status": "running",
        "description": "基于AI的学生作品多维度评估与诊断系统"
    }