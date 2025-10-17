"""学生信息服务"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models.student_auth import StudentAccount, DiagnosticRecord

logger = logging.getLogger(__name__)


class StudentServiceError(Exception):
    """学生服务异常"""
    pass


class StudentService:
    """
    学生信息服务
    
    管理学生的诊断历史、学习记录等信息
    """
    
    def __init__(self, storage_path: str = "./data/students"):
        """
        初始化学生服务
        
        Args:
            storage_path: 数据存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.diagnostic_path = self.storage_path / "diagnostics"
        self.diagnostic_path.mkdir(exist_ok=True)
        
        logger.info("👤 学生信息服务已初始化")
    
    def save_diagnostic_record(self, record: DiagnosticRecord) -> bool:
        """
        保存诊断记录
        
        Args:
            record: 诊断记录
            
        Returns:
            是否成功
        """
        try:
            # 学生诊断记录文件
            student_diagnostic_file = self.diagnostic_path / f"{record.student_id}.json"
            
            # 加载现有记录
            records = []
            if student_diagnostic_file.exists():
                with open(student_diagnostic_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            # 添加新记录
            records.append(record.to_dict())
            
            # 保存
            with open(student_diagnostic_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 保存诊断记录: {record.student_id} - {record.test_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存诊断记录失败: {str(e)}")
            return False
    
    def get_diagnostic_history(
        self, 
        student_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取诊断历史
        
        Args:
            student_id: 学生ID
            limit: 返回记录数量限制
            
        Returns:
            诊断记录列表
        """
        try:
            student_diagnostic_file = self.diagnostic_path / f"{student_id}.json"
            
            if not student_diagnostic_file.exists():
                return []
            
            with open(student_diagnostic_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            # 按时间降序排序
            records.sort(key=lambda x: x['submitted_at'], reverse=True)
            
            # 限制数量
            if limit:
                records = records[:limit]
            
            logger.info(f"📊 获取诊断历史: {student_id}, 共{len(records)}条")
            return records
            
        except Exception as e:
            logger.error(f"❌ 获取诊断历史失败: {str(e)}")
            return []
    
    def get_latest_diagnostic(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最新的诊断记录
        
        Args:
            student_id: 学生ID
            
        Returns:
            最新诊断记录
        """
        history = self.get_diagnostic_history(student_id, limit=1)
        return history[0] if history else None
    
    def get_learning_history(
        self,
        student_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取学习历史记录
        
        Args:
            student_id: 学生ID
            limit: 返回记录数量
            offset: 偏移量
            
        Returns:
            包含记录列表和总数的字典
        """
        try:
            # 从assessments.json文件读取学习记录
            assessments_file = Path("./storage/assessments.json")
            if not assessments_file.exists():
                return {"count": 0, "records": []}
            
            # 读取所有评估记录
            with open(assessments_file, 'r', encoding='utf-8') as f:
                all_assessments = json.load(f)
            
            # 筛选该学生的评估记录
            records = []
            logger.info(f"📊 开始筛选学生 {student_id} 的评估记录，总记录数: {len(all_assessments)}")
            
            for assessment_id, assessment_data in all_assessments.items():
                if assessment_data.get("student_id") == student_id:
                    # 计算综合分数
                    score_breakdown = assessment_data.get("score_breakdown", {})
                    idea_score = score_breakdown.get("idea", 0)
                    ui_score = score_breakdown.get("ui", 0)
                    code_score = score_breakdown.get("code", 0)
                    final_score = round((idea_score + ui_score + code_score) / 3, 1)
                    
                    # 简化记录格式
                    record = {
                        "assessment_id": assessment_id,
                        "student_id": assessment_data.get("student_id"),
                        "submitted_at": assessment_data.get("created_at"),
                        "final_score": final_score,
                        "status": assessment_data.get("status", "completed")
                    }
                    records.append(record)
            
            # 按时间降序排序
            records.sort(key=lambda x: x['submitted_at'], reverse=True)
            
            # 分页
            total_count = len(records)
            records = records[offset:offset + limit]
            
            logger.info(f"📚 获取学习历史: {student_id}, 共{total_count}条记录")
            logger.info(f"📚 学习记录详情: {[r['assessment_id'] + ':' + str(r['final_score']) for r in records[:3]]}")
            return {
                "count": total_count,
                "records": records
            }
            
        except Exception as e:
            logger.error(f"❌ 获取学习历史失败: {str(e)}")
            return {"count": 0, "records": []}
    
    def get_learning_statistics(self, student_id: str) -> Dict[str, Any]:
        """
        获取学习统计信息
        
        Args:
            student_id: 学生ID
            
        Returns:
            统计信息
        """
        try:
            # 获取诊断历史
            diagnostic_history = self.get_diagnostic_history(student_id)
            latest_diagnostic = diagnostic_history[0] if diagnostic_history else None
            
            # 获取学习历史
            learning_data = self.get_learning_history(student_id, limit=1000)
            learning_records = learning_data["records"]
            
            # 获取学习路径进度
            from ..services.learning_path_service import LearningPathService
            path_service = LearningPathService()
            student_progress = path_service.get_student_progress(student_id)
            
            logger.info(f"📊 获取学习统计 - 学生: {student_id}")
            logger.info(f"📊 学习路径进度数据: {student_progress}")
            
            # 计算学习路径完成率
            completion_rate = 0
            if student_progress and student_progress.completed_nodes:
                # 假设总共有7个学习节点
                total_nodes = 7
                completed_count = len(student_progress.completed_nodes)
                completion_rate = round((completed_count / total_nodes) * 100, 1)
                logger.info(f"📊 学习路径完成率计算: {completed_count}/{total_nodes} = {completion_rate}%")
            else:
                logger.info(f"📊 学习路径进度为空或不存在")
            
            # 计算统计
            stats = {
                "total_diagnostics": len(diagnostic_history),
                "total_assessments": learning_data["count"],
                "latest_diagnostic": latest_diagnostic,
                "average_score": 0,
                "completion_rate": completion_rate,
                "last_activity": None
            }
            
            # 计算平均分
            if learning_records:
                total_score = sum(r.get("final_score", 0) for r in learning_records)
                stats["average_score"] = round(total_score / len(learning_records), 1)
                stats["last_activity"] = learning_records[0]["submitted_at"]
                logger.info(f"📊 平均分计算: {total_score}/{len(learning_records)} = {stats['average_score']}")
            
            logger.info(f"📊 最终统计数据: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取学习统计失败: {str(e)}")
            return {}
    
    def get_student_profile(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        获取学生完整档案
        
        Args:
            student_id: 学生ID
            
        Returns:
            学生档案
        """
        try:
            # 从auth service获取基本信息
            from .auth_service import get_auth_service
            auth_service = get_auth_service()
            student_account = auth_service.get_student(student_id)
            
            if not student_account:
                return None
            
            # 获取统计信息
            stats = self.get_learning_statistics(student_id)
            
            # 组合完整档案
            profile = student_account.to_safe_dict()
            profile.update({
                "statistics": stats
            })
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ 获取学生档案失败: {str(e)}")
            return None


# 创建全局单例
_student_service = None


def get_student_service() -> StudentService:
    """获取学生服务单例"""
    global _student_service
    if _student_service is None:
        _student_service = StudentService()
    return _student_service
