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
from ..config.settings import assessment_config, path_config
from .learning_path_service import LearningPathService
from ..models.learning_path import NodeStatus


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
            self.learning_path_service = LearningPathService()
            
            self._initialized = True
            
        # 确保 storage 属性始终存在（处理单例重启问题）
        if not hasattr(self, 'storage'):
            self.storage = get_storage()
            self.assessments = self.storage.list_assessments()
            logger.info(f"📋 AssessmentService 存储已初始化，加载了 {len(self.assessments)} 条历史记录")
        elif not hasattr(self, 'assessments'):
            self.assessments = self.storage.list_assessments()
            logger.info(f"📋 AssessmentService 评估记录已重新加载，共 {len(self.assessments)} 条")
        
        # 确保学习路径服务可用
        if not hasattr(self, 'learning_path_service'):
            self.learning_path_service = LearningPathService()
    
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
                # 构建详细的分数结构
                score_breakdown = assessment.get("score_breakdown", {})
                detailed_scores = assessment.get("detailed_scores")
                
                # 如果有详细评分，提取子维度分数
                breakdown_data = {}
                if isinstance(score_breakdown, dict):
                    breakdown_data = score_breakdown
                else:
                    # 如果是对象，转换为字典
                    breakdown_data = {
                        "idea": getattr(score_breakdown, 'idea', 0),
                        "ui": getattr(score_breakdown, 'ui', 0), 
                        "code": getattr(score_breakdown, 'code', 0)
                    }
                
                # 添加详细的子维度分数
                if detailed_scores:
                    if hasattr(detailed_scores, 'idea'):
                        breakdown_data["idea_detail"] = {
                            "innovation": getattr(detailed_scores.idea, 'innovation', breakdown_data.get('idea', 0)),
                            "feasibility": getattr(detailed_scores.idea, 'feasibility', breakdown_data.get('idea', 0)),
                            "learning_value": getattr(detailed_scores.idea, 'learning_value', breakdown_data.get('idea', 0))
                        }
                    if hasattr(detailed_scores, 'ui'):
                        breakdown_data["ui_detail"] = {
                            "compliance": getattr(detailed_scores.ui, 'compliance', breakdown_data.get('ui', 0)),
                            "usability": getattr(detailed_scores.ui, 'usability', breakdown_data.get('ui', 0)),
                            "information_arch": getattr(detailed_scores.ui, 'information_arch', breakdown_data.get('ui', 0))
                        }
                    if hasattr(detailed_scores, 'code'):
                        breakdown_data["code_detail"] = {
                            "correctness": getattr(detailed_scores.code, 'correctness', breakdown_data.get('code', 0)),
                            "readability": getattr(detailed_scores.code, 'readability', breakdown_data.get('code', 0)),
                            "architecture": getattr(detailed_scores.code, 'architecture', breakdown_data.get('code', 0)),
                            "performance": getattr(detailed_scores.code, 'performance', breakdown_data.get('code', 0))
                        }
                
                result.update({
                    "overall_score": assessment.get("overall_score"),
                    "assessment_level": assessment.get("assessment_level"),
                    "breakdown": breakdown_data,
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
                # 构建基本评分数据
                breakdown_data = {}
                if assessment.score_breakdown:
                    breakdown_data = {
                        "idea": assessment.score_breakdown.idea,
                        "ui": assessment.score_breakdown.ui,
                        "code": assessment.score_breakdown.code
                    }
                
                # 添加详细的子维度分数
                if hasattr(assessment, 'detailed_scores') and assessment.detailed_scores:
                    if hasattr(assessment.detailed_scores, 'idea'):
                        breakdown_data["idea_detail"] = {
                            "innovation": assessment.detailed_scores.idea.innovation,
                            "feasibility": assessment.detailed_scores.idea.feasibility,
                            "learning_value": assessment.detailed_scores.idea.learning_value
                        }
                    if hasattr(assessment.detailed_scores, 'ui'):
                        breakdown_data["ui_detail"] = {
                            "compliance": assessment.detailed_scores.ui.compliance,
                            "usability": assessment.detailed_scores.ui.usability,
                            "information_arch": assessment.detailed_scores.ui.information_arch
                        }
                    if hasattr(assessment.detailed_scores, 'code'):
                        breakdown_data["code_detail"] = {
                            "correctness": assessment.detailed_scores.code.correctness,
                            "readability": assessment.detailed_scores.code.readability,
                            "architecture": assessment.detailed_scores.code.architecture,
                            "performance": assessment.detailed_scores.code.performance
                        }
                
                result.update({
                    "overall_score": assessment.overall_score,
                    "assessment_level": assessment.assessment_level.value if assessment.assessment_level else None,
                    "breakdown": breakdown_data,
                    "diagnosis": [
                        {
                            "dimension": d.dimension,
                            "issue": d.issue,
                            "fix": d.fix,
                            "priority": getattr(d, 'priority', 1)
                        } for d in assessment.diagnosis
                    ],
                    "resources": assessment.resources,
                    "exit_rules": {
                        "pass_status": assessment.exit_rules.pass_status,
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
            assessment.detailed_scores = result.get("detailed_scores")  # 保存详细评分
            assessment.diagnosis = result["diagnoses"]
            assessment.resources = result["resources"]
            assessment.exit_rules = result["exit_rules"]
            assessment.completed_at = datetime.now()
            assessment.updated_at = datetime.now()
            
            # 更新存储的记录
            self.assessments[assessment_id] = assessment
            self.storage.save_assessment(assessment_id, assessment)
            
            logger.info(f"📋 🎉 评估完成并保存: {assessment_id}, 总分: {result['overall_score']}")
            
            # 🆕 集成学习路径推荐系统（可通过配置开关控制）
            if path_config.enable_path_integration:
                await self._update_learning_path(assessment_id, assessment)
            else:
                logger.info(f"📋 ℹ️ 学习路径集成已禁用，跳过路径更新: {assessment_id}")
            
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
    
    async def _update_learning_path(self, assessment_id: str, assessment):
        """
        🆕 更新学习路径进度
        
        当评估完成后，自动调用学习路径服务来：
        1. 更新学生的节点进度
        2. 根据评估结果推荐下一步路径
        """
        try:
            student_id = assessment.student_id
            
            # 从评估结果中推断当前学习的节点
            current_node_id = self._infer_current_node(assessment.deliverables)
            
            # 构建评估结果数据
            assessment_result = {
                "overall_score": assessment.overall_score,
                "breakdown": {
                    "idea": assessment.score_breakdown.idea,
                    "ui": assessment.score_breakdown.ui,
                    "code": assessment.score_breakdown.code
                },
                "diagnosis": [
                    {
                        "dimension": d.dimension,
                        "issue": d.issue,
                        "fix": d.fix
                    } for d in assessment.diagnosis
                ],
                "exit_rules": {
                    "pass_status": assessment.exit_rules.pass_status,
                    "path_update": assessment.exit_rules.path_update,
                    "remedy": assessment.exit_rules.remedy
                } if assessment.exit_rules else None
            }
            
            # 确定节点状态
            if assessment.overall_score >= 60:  # 通过门槛
                node_status = NodeStatus.COMPLETED
            else:
                node_status = NodeStatus.FAILED
            
            logger.info(f"📚🤖 开始更新学习路径: {student_id} -> {current_node_id} -> {node_status.value}")
            
            # 更新学生进度
            await self.learning_path_service.update_student_progress(
                student_id=student_id,
                node_id=current_node_id,
                status=node_status,
                assessment_result=assessment_result
            )
            
            # 如果节点完成，生成路径推荐
            if node_status == NodeStatus.COMPLETED:
                recommendation = await self.learning_path_service.recommend_next_step(
                    student_id=student_id,
                    assessment_result=assessment_result
                )
                logger.info(f"📚🤖 路径推荐已生成: {student_id} -> {recommendation.recommended_channel.value}通道 -> {recommendation.next_node_id}")
            
            logger.info(f"📚🤖 ✅ 学习路径更新成功: {assessment_id}")
            
        except Exception as e:
            # 学习路径更新失败不应该影响评估结果
            logger.warning(f"📚🤖 ⚠️ 学习路径更新失败，但评估已完成: {assessment_id}, 错误: {str(e)}")
    
    def _infer_current_node(self, deliverables) -> str:
        """
        🆕 根据提交物推断当前学习节点
        
        基于学生提交的作业内容，智能推断当前正在学习的课程节点
        """
        
        # 分析提交物内容特征
        idea_text = deliverables.idea_text.lower() if deliverables.idea_text else ""
        code_snippets = " ".join(deliverables.code_snippets).lower() if deliverables.code_snippets else ""
        has_ui_images = len(deliverables.ui_images) > 0 if deliverables.ui_images else False
        
        # 节点关键词映射
        node_keywords = {
            "api_calling": ["api", "调用", "接口", "请求", "response", "http", "rest"],
            "model_deployment": ["模型", "部署", "docker", "ollama", "部署", "推理", "服务"],
            "no_code_ai": ["dify", "零代码", "无代码", "flow", "工作流", "配置"],
            "rag_system": ["rag", "检索", "向量", "faiss", "embedding", "知识库", "文档"],
            "ui_design": ["ui", "界面", "设计", "用户体验", "原型", "交互"],
            "frontend_dev": ["前端", "react", "vue", "html", "css", "javascript", "组件"],
            "backend_dev": ["后端", "api", "数据库", "服务器", "fastapi", "flask", "接口"]
        }
        
        # 计算每个节点的匹配得分
        node_scores = {}
        for node_id, keywords in node_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in idea_text:
                    score += 2  # idea中的关键词权重更高
                if keyword in code_snippets:
                    score += 3  # 代码中的关键词权重最高
            
            # UI相关的特殊处理
            if node_id == "ui_design" and has_ui_images:
                score += 5
            
            node_scores[node_id] = score
        
        # 找到得分最高的节点
        if node_scores:
            best_node = max(node_scores, key=node_scores.get)
            max_score = node_scores[best_node]
            
            # 如果得分过低，使用默认推断逻辑
            if max_score < 2:
                return self._default_node_inference()
            
            logger.info(f"📚🤖 节点推断: {best_node} (得分: {max_score})")
            return best_node
        
        return self._default_node_inference()
    
    def _default_node_inference(self) -> str:
        """默认节点推断逻辑"""
        # 简单策略：返回最常见的节点或者按顺序推断
        return "api_calling"  # 默认为第一个节点

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