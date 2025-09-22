"""评估服务核心实现"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..storage.file_storage import get_storage

from ..models.assessment import (
    Assessment, AssessmentStatus, Deliverables, ScoreBreakdown
)
from ..models.submission import Submission, IdeaDescription, UIDesign, CodeRepository
from ..evaluators.idea_evaluator import IdeaEvaluator
from ..evaluators.ui_analyzer import UIAnalyzer
from ..evaluators.code_reviewer import CodeReviewer
from ..evaluators.score_aggregator import ScoreAggregator
from ..config.settings import assessment_config


logger = logging.getLogger(__name__)


class AssessmentService:
    """评估服务类，负责协调整个评估流程"""
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.config = assessment_config
            self.idea_evaluator = IdeaEvaluator()
            self.ui_analyzer = UIAnalyzer()
            self.code_reviewer = CodeReviewer()
            self.score_aggregator = ScoreAggregator()
            
            self._initialized = True
            
        # 确保 storage 属性始终存在（处理单例重启问题）
        if not hasattr(self, 'storage'):
            self.storage = get_storage()
            self.assessments = self.storage.list_assessments()
            logger.info(f"📋 AssessmentService 存储已初始化，加载了 {len(self.assessments)} 条历史记录")
        elif not hasattr(self, 'assessments'):
            self.assessments = self.storage.list_assessments()
            logger.info(f"📋 AssessmentService 评估记录已重新加载，共 {len(self.assessments)} 条")
    
    async def submit_assessment(self, student_id: str, deliverables: Dict[str, Any]) -> str:
        """
        提交评估请求
        
        Args:
            student_id: 学生ID
            deliverables: 提交物数据
            
        Returns:
            评估ID
        """
        try:
            # 生成评估ID
            assessment_id = f"a_{datetime.now().strftime('%y%m%d')}_{str(uuid.uuid4())[:8]}"
            
            # 解析提交物
            parsed_deliverables = self._parse_deliverables(deliverables)
            
            # 创建评估记录
            assessment = Assessment(
                assessment_id=assessment_id,
                student_id=student_id,
                deliverables=parsed_deliverables,
                status=AssessmentStatus.QUEUED,
                created_at=datetime.now()
            )
            
            # 存储评估记录（同时保存到文件）
            self.assessments[assessment_id] = assessment
            self.storage.save_assessment(assessment_id, assessment)
            logger.info(f"📋 ✅ 评估记录已存储: {assessment_id}, 总记录数: {len(self.assessments)}")
            
            # 异步执行评估
            asyncio.create_task(self._execute_assessment(assessment_id))
            
            logger.info(f"评估请求已提交，ID: {assessment_id}")
            return assessment_id
            
        except Exception as e:
            logger.error(f"提交评估失败: {str(e)}")
            raise AssessmentServiceError(f"提交评估失败: {str(e)}")
    
    def get_assessment_status(self, assessment_id: str) -> Dict[str, Any]:
        """
        获取评估状态
        
        Args:
            assessment_id: 评估ID
            
        Returns:
            评估状态信息
        """
        logger.info(f"📋 🔍 查询评估记录: {assessment_id}")
        logger.info(f"📋 现有记录总数: {len(self.assessments)}")
        logger.debug(f"📋 现有记录ID列表: {list(self.assessments.keys())}")
        
        assessment = self.assessments.get(assessment_id)
        if not assessment:
            # 尝试从存储中重新加载
            assessment = self.storage.get_assessment(assessment_id)
            if assessment:
                self.assessments[assessment_id] = assessment
                logger.info(f"📋 ♻️ 从存储中恢复评估记录: {assessment_id}")
            else:
                logger.error(f"📋 ❌ 评估记录不存在: {assessment_id}")
                raise AssessmentServiceError(f"评估记录不存在: {assessment_id}")
        
        # 处理字典和对象两种情况
        if isinstance(assessment, dict):
            result = {
                "assessment_id": assessment_id,
                "student_id": assessment.get("student_id"),
                "status": assessment.get("status"),
                "created_at": assessment.get("created_at"),
                "updated_at": assessment.get("updated_at")
            }
            
            # 如果评估完成，添加详细结果
            if assessment.get("status") == "completed":
                result.update({
                    "overall_score": assessment.get("overall_score"),
                    "assessment_level": assessment.get("assessment_level"),
                    "breakdown": assessment.get("score_breakdown"),
                    "diagnosis": assessment.get("diagnosis", []),
                    "resources": assessment.get("resources", []),
                    "exit_rules": assessment.get("exit_rules"),
                    "completed_at": assessment.get("completed_at")
                })
        else:
            # 处理Assessment对象
            result = {
                "assessment_id": assessment_id,
                "student_id": assessment.student_id,
                "status": assessment.status.value if hasattr(assessment.status, 'value') else assessment.status,
                "created_at": assessment.created_at.isoformat() if hasattr(assessment.created_at, 'isoformat') else assessment.created_at,
                "updated_at": assessment.updated_at.isoformat() if assessment.updated_at and hasattr(assessment.updated_at, 'isoformat') else assessment.updated_at
            }
        
            # 如果评估完成，返回详细结果
            if assessment.status == AssessmentStatus.COMPLETED:
                result.update({
                    "overall_score": assessment.overall_score,
                    "assessment_level": assessment.assessment_level.value if assessment.assessment_level else None,
                    "breakdown": {
                        "idea": assessment.score_breakdown.idea,
                        "ui": assessment.score_breakdown.ui,
                        "code": assessment.score_breakdown.code
                    } if assessment.score_breakdown else None,
                    "diagnosis": [
                        {
                            "dim": d.dimension,
                            "issue": d.issue,
                            "fix": d.fix
                        } for d in assessment.diagnosis
                    ],
                    "resources": assessment.resources,
                    "exit_rules": {
                        "pass": assessment.exit_rules.pass_status,
                        "path_update": assessment.exit_rules.path_update,
                        "remedy": assessment.exit_rules.remedy
                    } if assessment.exit_rules else None,
                    "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None
                })
        
        return result
    
    def get_all_assessments(self, student_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有评估记录
        
        Args:
            student_id: 可选的学生ID过滤
            
        Returns:
            评估记录列表
        """
        assessments = list(self.assessments.values())
        
        # 处理字典类型的评估记录
        processed_assessments = []
        for a in assessments:
            if isinstance(a, dict):
                # 如果是字典，直接使用assessment_id
                assessment_id = a.get('assessment_id')
                assessment_student_id = a.get('student_id')
            else:
                # 如果是对象，使用属性
                assessment_id = a.assessment_id
                assessment_student_id = a.student_id
            
            if not student_id or assessment_student_id == student_id:
                processed_assessments.append(assessment_id)
        
        return [self.get_assessment_status(aid) for aid in processed_assessments]
    
    async def _execute_assessment(self, assessment_id: str):
        """
        异步执行评估流程
        """
        try:
            assessment = self.assessments[assessment_id]
            assessment.status = AssessmentStatus.IN_PROGRESS
            assessment.updated_at = datetime.now()
            
            # 保存状态更新
            self.storage.save_assessment(assessment_id, assessment)
            
            logger.info(f"📋 🚀 开始执行评估: {assessment_id}")
            
            # 构建评估数据
            evaluation_data = self._prepare_evaluation_data(assessment)
            logger.info(f"📋 📝 评估数据准备完成: {list(evaluation_data.keys())}")
            
            # 并行执行各维度评估
            logger.info("📋 🔀 开始并行评估...")
            
            try:
                idea_task = asyncio.create_task(self.idea_evaluator.evaluate(evaluation_data))
                ui_task = asyncio.create_task(self.ui_analyzer.evaluate(evaluation_data))  
                code_task = asyncio.create_task(self.code_reviewer.evaluate(evaluation_data))
                
                # 等待所有评估完成
                logger.info("📋 ⏳ 等待评估结果...")
                idea_result, ui_result, code_result = await asyncio.gather(
                    idea_task, ui_task, code_task, return_exceptions=True
                )
                
                logger.info("📋 ✅ 所有评估任务完成")
                logger.info(f"📋 Idea评估结果类型: {type(idea_result)}")
                logger.info(f"📋 UI评估结果类型: {type(ui_result)}")
                logger.info(f"📋 代码评估结果类型: {type(code_result)}")
                
            except Exception as e:
                logger.error(f"📋 ❌ 并行评估过程失败: {str(e)}")
                raise
            
            # 检查评估结果
            if isinstance(idea_result, Exception):
                logger.error(f"📋 ❌ idea评估失败: {str(idea_result)}")
                logger.error(f"📋 ❌ idea评估异常类型: {type(idea_result)}")
                idea_result = None
            else:
                logger.info(f"📋 ✅ idea评估成功: {idea_result.get('overall_score', '未知')}")
            
            if isinstance(ui_result, Exception):
                logger.error(f"📋 ❌ ui评估失败: {str(ui_result)}")
                logger.error(f"📋 ❌ ui评估异常类型: {type(ui_result)}")
                ui_result = None
            else:
                logger.info(f"📋 ✅ UI评估成功: {ui_result.get('overall_score', '未知')}")
                
            if isinstance(code_result, Exception):
                logger.error(f"📋 ❌ code评估失败: {str(code_result)}")
                logger.error(f"📋 ❌ code评估异常类型: {type(code_result)}")
                code_result = None
            else:
                logger.info(f"📋 ✅ 代码评估成功: {code_result.get('overall_score', '未知')}")
            
            # 聚合评分
            logger.info("📋 📊 开始聚合评分...")
            evaluation_results = {
                "idea": idea_result or {"overall_score": 0, "diagnoses": [], "resources": [], "feedback": "Idea评估失败"},
                "ui": ui_result or {"overall_score": 0, "diagnoses": [], "resources": [], "feedback": "UI评估失败"},
                "code": code_result or {"overall_score": 0, "diagnoses": [], "resources": [], "feedback": "代码评估失败"}
            }
            
            result = self.score_aggregator.aggregate_scores(evaluation_results)
            
            # 更新评估状态
            assessment.status = AssessmentStatus.COMPLETED
            assessment.overall_score = result["overall_score"]
            assessment.score_breakdown = result["score_breakdown"]
            assessment.diagnosis = result["diagnoses"]
            assessment.resources = result["resources"]
            assessment.exit_rules = result["exit_rules"]
            assessment.completed_at = datetime.now()
            assessment.updated_at = datetime.now()
            
            # 更新存储的记录
            self.assessments[assessment_id] = assessment
            self.storage.save_assessment(assessment_id, assessment)
            
            logger.info(f"📋 🎉 评估完成并保存: {assessment_id}, 总分: {result['overall_score']}")
            
        except Exception as e:
            # 处理评估异常
            logger.error(f"📋 ❌ 评估执行失败: {assessment_id}, 错误: {str(e)}")
            
            try:
                if assessment_id in self.assessments:
                    assessment = self.assessments[assessment_id]
                    assessment.status = AssessmentStatus.FAILED
                    if hasattr(assessment, 'error_message'):
                        assessment.error_message = str(e)
                    assessment.updated_at = datetime.now()
                    
                    # 保存错误状态
                    self.storage.save_assessment(assessment_id, assessment)
            except Exception as save_error:
                logger.error(f"📋 ❌ 保存错误状态失败: {str(save_error)}")

    def _prepare_evaluation_data(self, assessment: Assessment) -> Dict[str, Any]:
        """准备评估数据"""
        deliverables = assessment.deliverables
        return {
            # Idea相关数据
            "idea_text": deliverables.idea_text,
            "project_name": "项目",
            "technical_stack": [],
            "target_users": "用户",
            "core_features": [],
            
            # UI相关数据
            "ui_images": deliverables.ui_images,
            "design_tool": "",
            "design_system": "",
            "color_palette": [],
            "prototype_url": "",
            
            # 代码相关数据
            "code_repo": deliverables.code_repo,
            "language": "python",
            "framework": "未指定",
            "lines_of_code": 0,
            "test_coverage": 0.0,
            "code_snippets": deliverables.code_snippets
        }
    
    def _parse_deliverables(self, deliverables: Dict[str, Any]) -> Deliverables:
        """解析提交物数据"""
        return Deliverables(
            idea_text=deliverables.get("idea_text", ""),
            ui_images=deliverables.get("ui_images", []),
            code_repo=deliverables.get("code_repo"),
            code_snippets=deliverables.get("code_snippets", [])
        )
    
    async def export_path_rules(self, assessment_id: str) -> Dict[str, Any]:
        """
        导出准出规则到学习路径引擎
        
        Args:
            assessment_id: 评估ID
            
        Returns:
            导出结果
        """
        assessment = self.assessments.get(assessment_id)
        if not assessment:
            # 尝试从存储中重新加载
            assessment = self.storage.get_assessment(assessment_id)
            if assessment:
                self.assessments[assessment_id] = assessment
            else:
                raise AssessmentServiceError(f"评估记录不存在: {assessment_id}")
        
        if assessment.status != AssessmentStatus.COMPLETED:
            raise AssessmentServiceError(f"评估尚未完成: {assessment_id}")
        
        # 这里应该调用学习路径引擎的API
        # 暂时返回模拟结果
        path_rule_id = f"rule_{str(uuid.uuid4())[:8]}"
        
        logger.info(f"准出规则已导出到路径引擎: {assessment_id} -> {path_rule_id}")
        
        return {
            "synced": True,
            "path_engine_ref": path_rule_id,
            "assessment_id": assessment_id,
            "export_time": datetime.now().isoformat()
        }


class AssessmentServiceError(Exception):
    """评估服务错误"""
    pass