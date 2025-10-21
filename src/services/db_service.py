"""数据库访问服务层"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError

from ..config.database import get_db_session_context
from ..models.db_models import (
    Student, StudentProgress, StudentProgressNode, Diagnostic,
    AssessmentRun, Submission
)
from ..models.student import LearningLevel, LearningStyle
from ..models.learning_path import Channel, NodeStatus

logger = logging.getLogger(__name__)


class StudentDBService:
    """学生数据访问服务"""
    
    def create_student(self, student_data: Dict[str, Any]) -> Student:
        """创建学生"""
        with get_db_session_context() as session:
            try:
                student = Student(**student_data)
                session.add(student)
                session.commit()
                session.refresh(student)
                logger.info(f"📊 学生创建成功: {student.student_id}")
                return student
            except IntegrityError as e:
                session.rollback()
                logger.error(f"📊 学生创建失败，数据冲突: {str(e)}")
                raise ValueError(f"学生创建失败: {str(e)}")
            except Exception as e:
                session.rollback()
                logger.error(f"📊 学生创建失败: {str(e)}")
                raise
    
    def get_student(self, student_id: str) -> Optional[Student]:
        """获取学生信息"""
        with get_db_session_context() as session:
            student = session.query(Student).filter(Student.student_id == student_id).first()
            if student:
                # 在会话关闭前刷新对象，确保所有属性都被加载
                session.refresh(student)
            return student
    
    def get_student_for_auth(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取学生认证所需的信息（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            student = session.query(Student).filter(Student.student_id == student_id).first()
            if not student:
                return None
            
            # 在会话关闭前提取所需数据
            return {
                'student_id': student.student_id,
                'name': student.name,
                'email': student.email,
                'password_hash': student.password_hash,
                'created_at': student.created_at
            }
    
    def update_student(self, student_id: str, update_data: Dict[str, Any]) -> Optional[Student]:
        """更新学生信息"""
        with get_db_session_context() as session:
            try:
                student = session.query(Student).filter(Student.student_id == student_id).first()
                if not student:
                    return None
                
                for key, value in update_data.items():
                    if hasattr(student, key):
                        setattr(student, key, value)
                
                student.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(student)
                logger.info(f"📊 学生更新成功: {student_id}")
                return student
            except Exception as e:
                session.rollback()
                logger.error(f"📊 学生更新失败: {str(e)}")
                raise
    
    def delete_student(self, student_id: str) -> bool:
        """删除学生"""
        with get_db_session_context() as session:
            try:
                student = session.query(Student).filter(Student.student_id == student_id).first()
                if not student:
                    return False
                
                session.delete(student)
                session.commit()
                logger.info(f"📊 学生删除成功: {student_id}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"📊 学生删除失败: {str(e)}")
                raise
    
    def list_students(self, limit: int = 100, offset: int = 0) -> List[Student]:
        """获取学生列表"""
        with get_db_session_context() as session:
            return session.query(Student).offset(offset).limit(limit).all()


class StudentProgressDBService:
    """学生学习进度数据访问服务"""
    
    def create_progress(self, progress_data: Dict[str, Any]) -> StudentProgress:
        """创建学生进度"""
        with get_db_session_context() as session:
            try:
                progress = StudentProgress(**progress_data)
                session.add(progress)
                session.commit()
                session.refresh(progress)
                logger.info(f"📊 学生进度创建成功: {progress.student_id}")
                return progress
            except IntegrityError as e:
                session.rollback()
                logger.error(f"📊 学生进度创建失败，数据冲突: {str(e)}")
                raise ValueError(f"学生进度创建失败: {str(e)}")
            except Exception as e:
                session.rollback()
                logger.error(f"📊 学生进度创建失败: {str(e)}")
                raise
    
    def get_progress(self, student_id: str) -> Optional[StudentProgress]:
        """获取学生进度"""
        with get_db_session_context() as session:
            return session.query(StudentProgress).filter(StudentProgress.student_id == student_id).first()
    
    def update_progress(self, student_id: str, update_data: Dict[str, Any]) -> Optional[StudentProgress]:
        """更新学生进度"""
        with get_db_session_context() as session:
            try:
                progress = session.query(StudentProgress).filter(StudentProgress.student_id == student_id).first()
                if not progress:
                    return None
                
                for key, value in update_data.items():
                    if hasattr(progress, key):
                        setattr(progress, key, value)
                
                progress.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(progress)
                logger.info(f"📊 学生进度更新成功: {student_id}")
                return progress
            except Exception as e:
                session.rollback()
                logger.error(f"📊 学生进度更新失败: {str(e)}")
                raise
    
    def get_progress_nodes(self, student_id: str) -> List[StudentProgressNode]:
        """获取学生所有节点进度"""
        with get_db_session_context() as session:
            return session.query(StudentProgressNode).filter(
                StudentProgressNode.student_id == student_id
            ).order_by(StudentProgressNode.created_at).all()
    
    def get_progress_node(self, student_id: str, node_id: str) -> Optional[StudentProgressNode]:
        """获取学生特定节点进度"""
        with get_db_session_context() as session:
            return session.query(StudentProgressNode).filter(
                and_(
                    StudentProgressNode.student_id == student_id,
                    StudentProgressNode.node_id == node_id
                )
            ).first()
    
    def update_progress_node(self, student_id: str, node_id: str, update_data: Dict[str, Any]) -> Optional[StudentProgressNode]:
        """更新学生节点进度"""
        with get_db_session_context() as session:
            try:
                progress_node = session.query(StudentProgressNode).filter(
                    and_(
                        StudentProgressNode.student_id == student_id,
                        StudentProgressNode.node_id == node_id
                    )
                ).first()
                
                if not progress_node:
                    # 如果不存在，创建新的节点进度记录
                    progress_node = StudentProgressNode(
                        student_id=student_id,
                        node_id=node_id,
                        **update_data
                    )
                    session.add(progress_node)
                else:
                    # 更新现有记录
                    for key, value in update_data.items():
                        if hasattr(progress_node, key):
                            setattr(progress_node, key, value)
                
                progress_node.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(progress_node)
                logger.info(f"📊 学生节点进度更新成功: {student_id} - {node_id}")
                return progress_node
            except Exception as e:
                session.rollback()
                logger.error(f"📊 学生节点进度更新失败: {str(e)}")
                raise


class DiagnosticDBService:
    """诊断数据访问服务"""
    
    def create_diagnostic(self, diagnostic_data: Dict[str, Any]) -> Diagnostic:
        """创建诊断记录"""
        with get_db_session_context() as session:
            try:
                diagnostic = Diagnostic(**diagnostic_data)
                session.add(diagnostic)
                session.commit()
                session.refresh(diagnostic)
                logger.info(f"📊 诊断记录创建成功: {diagnostic.diagnostic_id}")
                return diagnostic
            except IntegrityError as e:
                session.rollback()
                logger.error(f"📊 诊断记录创建失败，数据冲突: {str(e)}")
                raise ValueError(f"诊断记录创建失败: {str(e)}")
            except Exception as e:
                session.rollback()
                logger.error(f"📊 诊断记录创建失败: {str(e)}")
                raise
    
    def get_diagnostic(self, diagnostic_id: str) -> Optional[Diagnostic]:
        """获取诊断记录"""
        with get_db_session_context() as session:
            return session.query(Diagnostic).filter(Diagnostic.diagnostic_id == diagnostic_id).first()
    
    def get_student_diagnostics(self, student_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取学生诊断记录列表（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            diagnostics = session.query(Diagnostic).filter(
                Diagnostic.student_id == student_id
            ).order_by(desc(Diagnostic.created_at)).limit(limit).all()
            
            # 在会话关闭前提取数据
            records = []
            for diagnostic in diagnostics:
                record = {
                    'diagnostic_id': diagnostic.diagnostic_id,
                    'student_id': diagnostic.student_id,
                    'diagnostic_type': diagnostic.diagnostic_type,
                    'overall_score': float(diagnostic.overall_score) if diagnostic.overall_score else None,
                    'concept_score': float(diagnostic.concept_score) if diagnostic.concept_score else None,
                    'coding_score': float(diagnostic.coding_score) if diagnostic.coding_score else None,
                    'tool_familiarity': float(diagnostic.tool_familiarity) if diagnostic.tool_familiarity else None,
                    'skill_scores': diagnostic.skill_scores or {},
                    'learning_style_preference': diagnostic.learning_style_preference,
                    'time_budget_hours_per_week': diagnostic.time_budget_hours_per_week,
                    'goals': diagnostic.goals or [],
                    'interests': diagnostic.interests or [],
                    'recommendations': diagnostic.recommendations or [],
                    'created_at': diagnostic.created_at
                }
                records.append(record)
            
            return records
    


class AssessmentDBService:
    """评分数据访问服务"""
    
    
    def create_assessment_run(self, run_data: Dict[str, Any]) -> AssessmentRun:
        """创建评分执行记录"""
        with get_db_session_context() as session:
            try:
                run = AssessmentRun(**run_data)
                session.add(run)
                session.commit()
                session.refresh(run)
                logger.info(f"📊 评分执行记录创建成功: {run.run_id}")
                return run
            except IntegrityError as e:
                session.rollback()
                logger.error(f"📊 评分执行记录创建失败，数据冲突: {str(e)}")
                raise ValueError(f"评分执行记录创建失败: {str(e)}")
            except Exception as e:
                session.rollback()
                logger.error(f"📊 评分执行记录创建失败: {str(e)}")
                raise
    
    def get_assessment_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """获取评分执行记录（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            run = session.query(AssessmentRun).filter(AssessmentRun.run_id == run_id).first()
            if not run:
                return None
            
            # 在会话关闭前提取数据
            return {
                'run_id': run.run_id,
                'student_id': run.student_id,
                'assessment_id': run.assessment_id,
                'node_id': run.node_id,
                'channel': run.channel if run.channel else None,
                'status': run.status if run.status else None,
                'overall_score': float(run.overall_score) if run.overall_score else None,
                'idea_score': float(run.idea_score) if run.idea_score else None,
                'ui_score': float(run.ui_score) if run.ui_score else None,
                'code_score': float(run.code_score) if run.code_score else None,
                'detailed_scores': run.detailed_scores,
                'assessment_level': run.assessment_level if run.assessment_level else None,
                'diagnosis': run.diagnosis,
                'resources': run.resources,
                'exit_rules': run.exit_rules,
                'error_message': run.error_message,
                'started_at': run.started_at,
                'completed_at': run.completed_at,
                'created_at': run.created_at,
                'updated_at': run.updated_at
            }
    
    def update_assessment_run(self, run_id: str, update_data: Dict[str, Any]) -> Optional[AssessmentRun]:
        """更新评分执行记录"""
        with get_db_session_context() as session:
            try:
                run = session.query(AssessmentRun).filter(AssessmentRun.run_id == run_id).first()
                if not run:
                    return None
                
                for key, value in update_data.items():
                    if hasattr(run, key):
                        # 处理特殊对象类型
                        if key == 'detailed_scores' and value is not None:
                            # 将DetailedScores对象转换为字典
                            if hasattr(value, '__dict__'):
                                value = {
                                    'idea': {
                                        'innovation': value.idea.innovation,
                                        'feasibility': value.idea.feasibility,
                                        'learning_value': value.idea.learning_value,
                                        'overall': value.idea.overall
                                    },
                                    'ui': {
                                        'compliance': value.ui.compliance,
                                        'usability': value.ui.usability,
                                        'information_arch': value.ui.information_arch,
                                        'overall': value.ui.overall
                                    },
                                    'code': {
                                        'correctness': value.code.correctness,
                                        'readability': value.code.readability,
                                        'architecture': value.code.architecture,
                                        'performance': value.code.performance,
                                        'overall': value.code.overall
                                    }
                                }
                        elif key == 'exit_rules' and value is not None:
                            # 将ExitRule对象转换为字典
                            if hasattr(value, '__dict__'):
                                value = {
                                    'must_pass': value.must_pass,
                                    'evidence_required': value.evidence_required,
                                    'time_limit': value.time_limit,
                                    'retry_allowed': value.retry_allowed
                                }
                        elif key == 'diagnosis' and value is not None:
                            # 将Diagnosis对象列表转换为字典列表
                            if isinstance(value, list):
                                value = [
                                    {
                                        'dimension': d.dimension,
                                        'issue': d.issue,
                                        'fix': d.fix,
                                        'priority': d.priority
                                    } if hasattr(d, '__dict__') else d
                                    for d in value
                                ]
                        
                        # 处理枚举字段（数据库中使用字符串枚举）
                        elif key == 'status' and isinstance(value, str):
                            # 验证状态值
                            valid_statuses = ['queued', 'in_progress', 'completed', 'failed']
                            if value not in valid_statuses:
                                logger.warning(f"无效的状态值: {value}，使用默认值: queued")
                                value = 'queued'
                        elif key == 'assessment_level' and isinstance(value, str):
                            # 验证评估等级值
                            valid_levels = ['pass', 'excellent', 'need_improvement']
                            if value not in valid_levels:
                                logger.warning(f"无效的评估等级值: {value}，使用默认值: pass")
                                value = 'pass'
                        elif key == 'channel' and isinstance(value, str):
                            # 验证通道值
                            valid_channels = ['A', 'B', 'C']
                            if value not in valid_channels:
                                logger.warning(f"无效的通道值: {value}，使用默认值: B")
                                value = 'B'
                        
                        setattr(run, key, value)
                
                run.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(run)
                logger.info(f"📊 评分执行记录更新成功: {run_id}")
                return run
            except Exception as e:
                session.rollback()
                logger.error(f"📊 评分执行记录更新失败: {str(e)}")
                raise
    
    def get_student_assessment_runs(self, student_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取学生评分执行记录列表（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            runs = session.query(AssessmentRun).filter(
                AssessmentRun.student_id == student_id
            ).order_by(desc(AssessmentRun.created_at)).limit(limit).all()
            
            # 在会话关闭前提取数据
            records = []
            for run in runs:
                record = {
                    'run_id': run.run_id,
                    'student_id': run.student_id,
                    'assessment_id': run.assessment_id,
                    'node_id': run.node_id,
                    'channel': run.channel if run.channel else None,
                    'status': run.status if run.status else None,
                    'overall_score': float(run.overall_score) if run.overall_score else None,
                    'idea_score': float(run.idea_score) if run.idea_score else None,
                    'ui_score': float(run.ui_score) if run.ui_score else None,
                    'code_score': float(run.code_score) if run.code_score else None,
                    'detailed_scores': run.detailed_scores,
                    'assessment_level': run.assessment_level if run.assessment_level else None,
                    'diagnosis': run.diagnosis,
                    'resources': run.resources,
                    'exit_rules': run.exit_rules,
                    'error_message': run.error_message,
                    'started_at': run.started_at,
                    'completed_at': run.completed_at,
                    'created_at': run.created_at,
                    'updated_at': run.updated_at
                }
                records.append(record)
            
            return records
    
    def get_submissions_by_assessment_run(self, assessment_run_id: str) -> List[Dict[str, Any]]:
        """根据评估执行ID获取提交记录（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            submissions = session.query(Submission).filter(
                Submission.assessment_run_id == assessment_run_id
            ).all()
            
            # 在会话关闭前提取数据
            result = []
            for submission in submissions:
                result.append({
                    'id': submission.id,
                    'submission_id': submission.submission_id,
                    'student_id': submission.student_id,
                    'node_id': submission.node_id,
                    'channel': submission.channel if submission.channel else None,
                    'assessment_run_id': submission.assessment_run_id,
                    'file_path': submission.file_path,
                    'file_type': submission.file_type,
                    'file_size': submission.file_size,
                    'content_hash': submission.content_hash,
                    'idea_text': submission.idea_text,
                    'ui_images': submission.ui_images,
                    'code_snippets': submission.code_snippets,
                    'code_repo': submission.code_repo,
                    'submission_type': submission.submission_type,
                    'status': submission.status if submission.status else None,
                    'created_at': submission.created_at,
                    'updated_at': submission.updated_at
                })
            
            return result


class SubmissionDBService:
    """提交数据访问服务"""
    
    def create_submission(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建提交记录（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            try:
                submission = Submission(**submission_data)
                session.add(submission)
                session.commit()
                session.refresh(submission)
                
                # 在会话关闭前提取数据
                result = {
                    'id': submission.id,
                    'submission_id': submission.submission_id,
                    'student_id': submission.student_id,
                    'node_id': submission.node_id,
                    'channel': submission.channel if submission.channel else None,
                    'assessment_run_id': submission.assessment_run_id,
                    'file_path': submission.file_path,
                    'file_type': submission.file_type,
                    'file_size': submission.file_size,
                    'content_hash': submission.content_hash,
                    'idea_text': submission.idea_text,
                    'ui_images': submission.ui_images,
                    'code_snippets': submission.code_snippets,
                    'code_repo': submission.code_repo,
                    'submission_type': submission.submission_type,
                    'status': submission.status if submission.status else None,
                    'created_at': submission.created_at,
                    'updated_at': submission.updated_at
                }
                
                logger.info(f"📊 提交记录创建成功: {submission.submission_id}")
                return result
            except IntegrityError as e:
                session.rollback()
                logger.error(f"📊 提交记录创建失败，数据冲突: {str(e)}")
                raise ValueError(f"提交记录创建失败: {str(e)}")
            except Exception as e:
                session.rollback()
                logger.error(f"📊 提交记录创建失败: {str(e)}")
                raise
    
    def get_submission(self, submission_id: str) -> Optional[Submission]:
        """获取提交记录"""
        with get_db_session_context() as session:
            return session.query(Submission).filter(Submission.submission_id == submission_id).first()
    
    def get_student_submissions(self, student_id: str, node_id: Optional[str] = None, limit: int = 50) -> List[Submission]:
        """获取学生提交记录列表"""
        with get_db_session_context() as session:
            query = session.query(Submission).filter(Submission.student_id == student_id)
            
            if node_id:
                query = query.filter(Submission.node_id == node_id)
            
            return query.order_by(desc(Submission.created_at)).limit(limit).all()
    
    def update_submission(self, submission_id: str, update_data: Dict[str, Any]) -> Optional[Submission]:
        """更新提交记录"""
        with get_db_session_context() as session:
            try:
                submission = session.query(Submission).filter(Submission.submission_id == submission_id).first()
                if not submission:
                    return None
                
                for key, value in update_data.items():
                    if hasattr(submission, key):
                        setattr(submission, key, value)
                
                submission.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(submission)
                logger.info(f"📊 提交记录更新成功: {submission_id}")
                return submission
            except Exception as e:
                session.rollback()
                logger.error(f"📊 提交记录更新失败: {str(e)}")
                raise
    
    def get_submissions_by_assessment_run(self, assessment_run_id: str) -> List[Dict[str, Any]]:
        """根据评估执行ID获取提交记录（返回字典避免会话问题）"""
        with get_db_session_context() as session:
            submissions = session.query(Submission).filter(
                Submission.assessment_run_id == assessment_run_id
            ).all()
            
            # 在会话关闭前提取数据
            result = []
            for submission in submissions:
                result.append({
                    'id': submission.id,
                    'submission_id': submission.submission_id,
                    'student_id': submission.student_id,
                    'node_id': submission.node_id,
                    'channel': submission.channel if submission.channel else None,
                    'assessment_run_id': submission.assessment_run_id,
                    'file_path': submission.file_path,
                    'file_type': submission.file_type,
                    'file_size': submission.file_size,
                    'content_hash': submission.content_hash,
                    'idea_text': submission.idea_text,
                    'ui_images': submission.ui_images,
                    'code_snippets': submission.code_snippets,
                    'code_repo': submission.code_repo,
                    'submission_type': submission.submission_type,
                    'status': submission.status if submission.status else None,
                    'created_at': submission.created_at,
                    'updated_at': submission.updated_at
                })
            
            return result


# LearningPathDBService 已移除，因为对应的数据库模型不存在
# 学习路径相关的功能通过 LearningPathService 和 ProgressRepository 处理
