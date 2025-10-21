"""学生信息服务"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..models.student_auth import StudentAccount, DiagnosticRecord
from ..services.db_service import StudentDBService, DiagnosticDBService, AssessmentDBService
from ..models.db_models import Diagnostic, DiagnosticItem

logger = logging.getLogger(__name__)


class StudentServiceError(Exception):
    """学生服务异常"""
    pass


class StudentService:
    """
    学生信息服务
    
    管理学生的诊断历史、学习记录等信息
    """
    
    def __init__(self):
        """
        初始化学生服务
        """
        self.student_db = StudentDBService()
        self.diagnostic_db = DiagnosticDBService()
        self.assessment_db = AssessmentDBService()
        
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
            # 创建诊断记录
            # 计算总体得分（基于各维度分数的平均值）
            overall_score = (record.concept_score + record.coding_score + record.tool_familiarity) / 3
            
            diagnostic_data = {
                'diagnostic_id': record.test_id,
                'student_id': record.student_id,
                'diagnostic_type': 'comprehensive',
                'overall_score': overall_score,
                'concept_score': record.concept_score,
                'coding_score': record.coding_score,
                'tool_familiarity': record.tool_familiarity,
                'skill_scores': getattr(record, 'skill_scores', {}),
                'learning_style_preference': getattr(record, 'learning_style_preference', record.learning_style),
                'time_budget_hours_per_week': getattr(record, 'time_budget_hours_per_week', 6),
                'goals': getattr(record, 'goals', []),
                'interests': record.interests,
                'recommendations': getattr(record, 'recommendations', []),
                'created_at': record.submitted_at
            }
            
            diagnostic = self.diagnostic_db.create_diagnostic(diagnostic_data)
            
            # 保存诊断题目明细（如果存在）
            diagnostic_items = getattr(record, 'diagnostic_items', [])
            for item in diagnostic_items:
                item_data = {
                    'diagnostic_id': record.test_id,
                    'item_id': item.get('item_id', ''),
                    'item_type': item.get('item_type', ''),
                    'question': item.get('question', ''),
                    'answer': item.get('answer', ''),
                    'correct_answer': item.get('correct_answer', ''),
                    'score': item.get('score'),
                    'max_score': item.get('max_score', 100.0),
                    'dimension': item.get('dimension', ''),
                    'difficulty_level': item.get('difficulty_level'),
                    'time_spent_seconds': item.get('time_spent_seconds'),
                    'created_at': record.submitted_at
                }
                self.diagnostic_db.create_diagnostic_item(item_data)
            
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
            # 从数据库获取诊断记录（已经是字典格式）
            records = self.diagnostic_db.get_student_diagnostics(
                student_id, 
                limit=limit or 10
            )
            
            # 转换字段名以保持API兼容性
            for record in records:
                record['test_id'] = record['diagnostic_id']
                record['submitted_at'] = record['created_at'].isoformat() if record['created_at'] else None
                record['created_at'] = record['created_at'].isoformat() if record['created_at'] else None
            
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
            # 从数据库获取评估记录
            assessment_runs = self.assessment_db.get_student_assessment_runs(
                student_id, 
                limit=limit + offset
            )
            
            # 转换为字典格式
            records = []
            for run in assessment_runs:
                # 计算综合分数
                idea_score = float(run['idea_score']) if run['idea_score'] else 0
                ui_score = float(run['ui_score']) if run['ui_score'] else 0
                code_score = float(run['code_score']) if run['code_score'] else 0
                final_score = round((idea_score + ui_score + code_score) / 3, 1) if (idea_score + ui_score + code_score) > 0 else 0
                
                # 构建score_breakdown
                score_breakdown = {
                    "idea": idea_score,
                    "ui": ui_score,
                    "code": code_score
                }
                
                record = {
                    "assessment_id": run['run_id'],
                    "student_id": run['student_id'],
                    "submitted_at": run['created_at'].isoformat() if run['created_at'] else None,
                    "created_at": run['created_at'].isoformat() if run['created_at'] else None,
                    "final_score": final_score,
                    "overall_score": run['overall_score'] if run['overall_score'] else final_score,
                    "status": run['status'],
                    "score_breakdown": score_breakdown,
                    "breakdown": score_breakdown,
                    "detailed_scores": run['detailed_scores'] or {},
                    "diagnosis": run['diagnosis'] or [],
                    "resources": run['resources'] or [],
                    "exit_rules": run['exit_rules'] or {},
                    "comprehensive_feedback": "",
                    "deliverables": {},
                    "raw_data": {
                        "run_id": run['run_id'],
                        "student_id": run['student_id'],
                        "assessment_id": run['assessment_id'],
                        "node_id": run['node_id'],
                        "channel": run['channel'],
                        "status": run['status'],
                        "overall_score": run['overall_score'],
                        "idea_score": idea_score,
                        "ui_score": ui_score,
                        "code_score": code_score,
                        "assessment_level": run['assessment_level'],
                        "created_at": run['created_at'].isoformat() if run['created_at'] else None,
                        "completed_at": run['completed_at'].isoformat() if run['completed_at'] else None
                    }
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
