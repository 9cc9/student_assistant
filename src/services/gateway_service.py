"""评估网关服务"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from .assessment_service import AssessmentService
from ..models.assessment import Assessment, AssessmentStatus
from ..config.settings import system_config


logger = logging.getLogger(__name__)


class GatewayService:
    """评估网关服务，作为评估系统的统一入口"""
    
    def __init__(self):
        self.assessment_service = AssessmentService()
        self.config = system_config
        
        # 请求队列和并发控制
        self.request_queue = None  # 懒加载
        self.active_assessments = set()
        self.max_concurrent = self.config.max_workers
        self._process_task = None  # 处理任务引用
        
    async def _ensure_initialized(self):
        """确保异步组件已初始化"""
        if self.request_queue is None:
            self.request_queue = asyncio.Queue()
        if self._process_task is None:
            self._process_task = asyncio.create_task(self._process_requests())
    
    async def submit_for_assessment(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提交评估请求的统一入口
        
        Args:
            request_data: 包含学生ID和提交物的请求数据
            
        Returns:
            包含assessment_id和status的响应
        """
        try:
            # 确保异步组件已初始化
            await self._ensure_initialized()
            # 验证请求数据
            self._validate_request(request_data)
            
            # 提取数据
            student_id = request_data["student_id"]
            deliverables = request_data["deliverables"]
            
            # 检查学生是否有进行中的评估
            existing_assessment = self._get_active_assessment(student_id)
            if existing_assessment:
                return {
                    "assessment_id": existing_assessment,
                    "status": "duplicate",
                    "message": "该学生已有正在进行的评估"
                }
            
            # 提交评估请求
            assessment_id = await self.assessment_service.submit_assessment(
                student_id, deliverables
            )
            
            # 记录活跃评估
            self.active_assessments.add(assessment_id)
            
            logger.info(f"评估请求已通过网关提交: {assessment_id}")
            
            return {
                "assessment_id": assessment_id,
                "status": "queued",
                "message": "评估请求已提交，正在处理中"
            }
            
        except Exception as e:
            logger.error(f"网关处理评估请求失败: {str(e)}")
            raise GatewayError(f"处理请求失败: {str(e)}")
    
    async def get_assessment_result(self, assessment_id: str) -> Dict[str, Any]:
        """
        获取评估结果
        
        Args:
            assessment_id: 评估ID
            
        Returns:
            评估结果
        """
        try:
            result = self.assessment_service.get_assessment_status(assessment_id)
            
            # 如果评估已完成，从活跃列表中移除
            if result["status"] in ["completed", "failed"]:
                self.active_assessments.discard(assessment_id)
            
            return result
            
        except Exception as e:
            logger.error(f"获取评估结果失败: {assessment_id}, 错误: {str(e)}")
            raise GatewayError(f"获取评估结果失败: {str(e)}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态信息
        """
        return {
            "status": "online",
            "active_assessments": len(self.active_assessments),
            "max_concurrent": self.max_concurrent,
            "queue_size": self.request_queue.qsize() if self.request_queue else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_assessment_history(self, student_id: Optional[str] = None, 
                              limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取评估历史记录
        
        Args:
            student_id: 可选的学生ID筛选
            limit: 返回记录数量限制
            
        Returns:
            评估历史记录列表
        """
        try:
            assessments = self.assessment_service.get_all_assessments(student_id)
            
            # 按时间倒序排序
            assessments.sort(key=lambda x: x["created_at"], reverse=True)
            
            return assessments[:limit]
            
        except Exception as e:
            logger.error(f"获取评估历史失败: {str(e)}")
            raise GatewayError(f"获取评估历史失败: {str(e)}")
    
    async def batch_submit_assessments(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量提交评估请求
        
        Args:
            requests: 评估请求列表
            
        Returns:
            批量提交结果
        """
        results = []
        
        # 并发处理多个请求
        tasks = [self.submit_for_assessment(request) for request in requests]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(result)
                })
            else:
                results.append({
                    "index": i,
                    **result
                })
        
        return results
    
    async def sync_to_path_engine(self, assessment_id: str) -> Dict[str, Any]:
        """
        同步评估结果到学习路径引擎
        
        Args:
            assessment_id: 评估ID
            
        Returns:
            同步结果
        """
        try:
            return await self.assessment_service.export_path_rules(assessment_id)
            
        except Exception as e:
            logger.error(f"同步到路径引擎失败: {assessment_id}, 错误: {str(e)}")
            raise GatewayError(f"同步失败: {str(e)}")
    
    def _validate_request(self, request_data: Dict[str, Any]):
        """验证请求数据格式"""
        required_fields = ["student_id", "deliverables"]
        
        for field in required_fields:
            if field not in request_data:
                raise GatewayError(f"缺少必填字段: {field}")
        
        deliverables = request_data["deliverables"]
        if not deliverables.get("idea_text") and not deliverables.get("ui_images") and \
           not deliverables.get("code_repo") and not deliverables.get("code_snippets"):
            raise GatewayError("至少需要提供一种类型的提交物")
    
    def _get_active_assessment(self, student_id: str) -> Optional[str]:
        """检查学生是否有进行中的评估"""
        try:
            assessments = self.assessment_service.get_all_assessments(student_id)
            
            for assessment in assessments:
                if assessment["status"] in ["queued", "in_progress"]:
                    return assessment["assessment_id"]
            
            return None
            
        except Exception:
            return None
    
    async def _process_requests(self):
        """处理请求队列（预留接口，用于更复杂的队列管理）"""
        while True:
            try:
                # 这里可以实现更复杂的请求处理逻辑
                # 比如优先级队列、限流等
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"请求处理器异常: {str(e)}")
                await asyncio.sleep(5)
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取评估统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            统计信息
        """
        try:
            assessments = self.assessment_service.get_all_assessments()
            
            # 过滤指定天数内的记录
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            recent_assessments = []
            for assessment in assessments:
                created_at = datetime.fromisoformat(assessment["created_at"])
                if created_at >= cutoff_date:
                    recent_assessments.append(assessment)
            
            # 计算统计信息
            total_count = len(recent_assessments)
            completed_count = len([a for a in recent_assessments if a["status"] == "completed"])
            failed_count = len([a for a in recent_assessments if a["status"] == "failed"])
            
            # 计算平均分
            completed_assessments = [a for a in recent_assessments 
                                   if a["status"] == "completed" and a.get("overall_score")]
            avg_score = sum(a["overall_score"] for a in completed_assessments) / len(completed_assessments) \
                       if completed_assessments else 0
            
            return {
                "period_days": days,
                "total_assessments": total_count,
                "completed_assessments": completed_count,
                "failed_assessments": failed_count,
                "success_rate": completed_count / total_count if total_count > 0 else 0,
                "average_score": round(avg_score, 2),
                "active_assessments": len(self.active_assessments)
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            raise GatewayError(f"获取统计信息失败: {str(e)}")


class GatewayError(Exception):
    """网关服务错误"""
    pass