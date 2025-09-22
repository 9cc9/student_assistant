"""系统API接口"""

from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from ..services import GatewayService


# 创建路由器
system_router = APIRouter(prefix="/api/system", tags=["System"])


# 依赖注入：获取网关服务实例
def get_gateway_service() -> GatewayService:
    """获取网关服务实例"""
    return GatewayService()


@system_router.get("/health", summary="系统健康检查")
async def health_check() -> Dict[str, Any]:
    """
    系统健康检查接口
    
    返回系统状态和版本信息
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "service": "AI助教评估系统",
        "components": {
            "assessment_engine": "running",
            "idea_evaluator": "running", 
            "ui_analyzer": "running",
            "code_reviewer": "running",
            "score_aggregator": "running"
        }
    }


@system_router.get("/status", summary="系统状态详情")
async def get_system_status(
    gateway: GatewayService = Depends(get_gateway_service)
) -> Dict[str, Any]:
    """
    获取系统详细状态信息
    
    返回系统运行统计、队列状态、性能指标等
    """
    try:
        stats = await gateway.get_system_statistics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_status": stats["system_status"],
            "assessment_statistics": {
                "total_assessments": stats["total_assessments"],
                "completed_assessments": stats["completed_assessments"],
                "failed_assessments": stats["failed_assessments"],
                "success_rate": round(stats["success_rate"] * 100, 2),
                "avg_processing_time": round(stats["avg_processing_time"], 2),
                "avg_overall_score": round(stats["avg_overall_score"], 1)
            },
            "queue_status": {
                "priority_queue": stats["priority_queue_length"],
                "normal_queue": stats["normal_queue_length"],
                "total_queued": stats["total_queued"]
            },
            "performance_metrics": {
                "uptime_hours": 24,  # 模拟运行时间
                "memory_usage_mb": 512,  # 模拟内存使用
                "cpu_usage_percent": 25,  # 模拟CPU使用率
                "response_time_ms": 150  # 模拟响应时间
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统状态失败: {str(e)}"
        )


@system_router.get("/statistics", summary="系统统计信息")
async def get_system_statistics(
    gateway: GatewayService = Depends(get_gateway_service)
) -> Dict[str, Any]:
    """
    获取系统统计信息
    
    返回评估系统的各项统计数据
    """
    try:
        stats = await gateway.get_system_statistics()
        
        return {
            "assessment_overview": {
                "total_assessments": stats["total_assessments"],
                "completed_assessments": stats["completed_assessments"],
                "success_rate": stats["success_rate"],
                "avg_processing_time": stats["avg_processing_time"],
                "avg_overall_score": stats["avg_overall_score"]
            },
            "queue_metrics": {
                "current_queue_length": stats["total_queued"],
                "priority_tasks": stats["priority_queue_length"],
                "normal_tasks": stats["normal_queue_length"]
            },
            "performance_indicators": {
                "system_load": "normal",
                "throughput_per_hour": max(1, stats["completed_assessments"]),
                "error_rate": 1 - stats["success_rate"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@system_router.get("/evaluators/status", summary="评估器状态")
async def get_evaluators_status() -> Dict[str, Any]:
    """
    获取各个评估器的状态信息
    
    返回Idea、UI、Code三个评估器的状态
    """
    return {
        "evaluators": {
            "idea_evaluator": {
                "status": "active",
                "version": "1.0.0",
                "weights": {
                    "innovation": 0.4,
                    "feasibility": 0.4,
                    "learning_value": 0.2
                },
                "last_updated": datetime.now().isoformat()
            },
            "ui_analyzer": {
                "status": "active",
                "version": "1.0.0",
                "weights": {
                    "compliance": 0.25,
                    "usability": 0.25,
                    "accessibility": 0.25,
                    "information_architecture": 0.25
                },
                "capabilities": [
                    "color_analysis",
                    "layout_detection",
                    "contrast_checking",
                    "ui_element_recognition"
                ]
            },
            "code_reviewer": {
                "status": "active",
                "version": "1.0.0", 
                "weights": {
                    "correctness": 0.15,
                    "robustness": 0.15,
                    "readability": 0.20,
                    "maintainability": 0.20,
                    "architecture": 0.15,
                    "performance": 0.08,
                    "security": 0.07
                },
                "supported_languages": [
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "cpp"
                ]
            }
        },
        "aggregator": {
            "status": "active",
            "category_weights": {
                "idea": 0.30,
                "ui": 0.30,
                "code": 0.40
            },
            "pass_threshold": 60.0,
            "excellent_threshold": 85.0
        }
    }


@system_router.post("/maintenance/clear-cache", summary="清理缓存")
async def clear_cache(
    gateway: GatewayService = Depends(get_gateway_service)
) -> Dict[str, Any]:
    """
    清理系统缓存
    
    清理评估结果缓存，释放内存
    """
    try:
        # 清理评估服务的内存存储(在真实系统中应该更谨慎)
        initial_count = len(gateway.assessment_service.assessments)
        
        # 只保留最近1小时的评估记录
        current_time = datetime.now()
        to_remove = []
        
        for assessment_id, assessment in gateway.assessment_service.assessments.items():
            time_diff = (current_time - assessment.created_at).total_seconds()
            if time_diff > 3600:  # 1小时 = 3600秒
                to_remove.append(assessment_id)
        
        # 删除过期记录
        for assessment_id in to_remove:
            del gateway.assessment_service.assessments[assessment_id]
            if assessment_id in gateway.assessment_service.assessment_results:
                del gateway.assessment_service.assessment_results[assessment_id]
        
        final_count = len(gateway.assessment_service.assessments)
        
        return {
            "success": True,
            "cleared_records": initial_count - final_count,
            "remaining_records": final_count,
            "timestamp": current_time.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理缓存失败: {str(e)}"
        )


@system_router.get("/config", summary="系统配置信息")
async def get_system_config() -> Dict[str, Any]:
    """
    获取系统配置信息
    
    返回当前系统的配置参数
    """
    return {
        "assessment_config": {
            "max_concurrent_assessments": 10,
            "default_timeout_seconds": 300,
            "retry_attempts": 3
        },
        "preprocessing_rules": {
            "min_idea_words": 50,
            "max_idea_words": 2000,
            "max_ui_images": 10,
            "max_code_files": 50,
            "max_file_size_mb": 10
        },
        "scoring_thresholds": {
            "pass_threshold": 60.0,
            "excellent_threshold": 85.0
        },
        "queue_settings": {
            "max_queue_size": 1000,
            "priority_queue_enabled": True,
            "batch_processing_enabled": True
        },
        "path_engine": {
            "enabled": True,
            "auto_sync": True,
            "retry_failed_syncs": True
        }
    }


@system_router.get("/version", summary="版本信息")
async def get_version_info() -> Dict[str, Any]:
    """
    获取系统版本信息
    
    返回系统各组件的版本号和构建信息
    """
    return {
        "system": {
            "name": "AI助教评估系统",
            "version": "1.0.0",
            "build_date": "2025-01-17",
            "environment": "development"
        },
        "components": {
            "fastapi": "0.104.1",
            "pydantic": "2.5.0",
            "python": "3.9+",
            "opencv": "4.8.1.78",
            "numpy": "1.24.4"
        },
        "api_version": "v1",
        "documentation": "/docs",
        "health_check": "/api/system/health"
    }


@system_router.get("/logs/recent", summary="最近日志")
async def get_recent_logs(
    limit: int = 50,
    level: str = "INFO"
) -> Dict[str, Any]:
    """
    获取最近的系统日志
    
    - **limit**: 返回日志条数限制
    - **level**: 日志级别过滤(DEBUG/INFO/WARNING/ERROR)
    
    返回最近的系统日志记录
    """
    # 模拟日志数据
    mock_logs = []
    current_time = datetime.now()
    
    for i in range(min(limit, 20)):  # 最多返回20条模拟日志
        log_time = current_time.replace(second=current_time.second - i * 10)
        mock_logs.append({
            "timestamp": log_time.isoformat(),
            "level": level,
            "component": "assessment_service",
            "message": f"处理评估任务 a_250117_{str(i).zfill(4)}",
            "details": {
                "student_id": f"s_2025_{str(i).zfill(3)}",
                "processing_time": round(25.5 + i * 0.5, 2)
            }
        })
    
    return {
        "total_logs": len(mock_logs),
        "level_filter": level,
        "logs": mock_logs
    }

