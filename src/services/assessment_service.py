"""评估服务核心实现"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..services.db_service import AssessmentDBService
from ..services.assessment_rule_service import get_assessment_rule_service

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
            self.db_service = AssessmentDBService()
            self.rule_service = get_assessment_rule_service()
            
            self._initialized = True
            
        # 完全使用数据库存储，移除文件存储依赖
        
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
            
            # 获取评分规则
            rule = self.rule_service.get_default_rule()
            if not rule:
                raise AssessmentServiceError("无法获取默认评分规则")
            
            # 创建评估执行记录（AssessmentRun是具体的评估执行记录）
            assessment_run_data = {
                'run_id': assessment_id,  # 使用相同的ID
                'student_id': student_id,
                'assessment_id': rule['rule_id'],  # 使用配置文件中的评分规则ID
                'node_id': rule.get('node_id', 'file_upload'),
                'channel': rule.get('channel', 'B'),
                'status': 'queued',
                'created_at': datetime.now()
            }
            
            # 存储到数据库
            self.db_service.create_assessment_run(assessment_run_data)
            logger.info(f"📋 ✅ 评估记录已存储到数据库: {assessment_id}")
            
            # 同步执行评估（避免异步任务问题）
            try:
                import threading
                def run_assessment():
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self._execute_assessment(assessment_id))
                    finally:
                        loop.close()
                
                # 在后台线程中执行评估
                thread = threading.Thread(target=run_assessment, daemon=True)
                thread.start()
                logger.info(f"📋 🚀 评估任务已在后台线程中启动: {assessment_id}")
            except Exception as e:
                logger.error(f"📋 ❌ 启动评估任务失败: {str(e)}")
                # 如果后台执行失败，至少更新状态为失败
                try:
                    self.db_service.update_assessment_run(assessment_id, {
                        'status': 'failed',
                        'error_message': f'启动评估任务失败: {str(e)}',
                        'updated_at': datetime.utcnow()
                    })
                except:
                    pass
            
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
        
        # 从数据库获取评估记录
        try:
            assessment_run = self.db_service.get_assessment_run(assessment_id)
            if not assessment_run:
                logger.error(f"📋 ❌ 评估记录不存在: {assessment_id}")
                raise AssessmentServiceError(f"评估记录不存在: {assessment_id}")
            
            # 转换为前端需要的格式
            assessment = {
                "assessment_id": assessment_run['run_id'],
                "student_id": assessment_run['student_id'],
                "status": assessment_run['status'],
                "created_at": assessment_run['created_at'].isoformat() if assessment_run['created_at'] else None,
                "updated_at": assessment_run['updated_at'].isoformat() if assessment_run['updated_at'] else None,
                "overall_score": assessment_run['overall_score'],
                "idea_score": assessment_run['idea_score'],
                "ui_score": assessment_run['ui_score'],
                "code_score": assessment_run['code_score'],
                "detailed_scores": assessment_run['detailed_scores'] or {},
                "diagnosis": assessment_run['diagnosis'] or [],
                "resources": assessment_run['resources'] or [],
                "exit_rules": assessment_run['exit_rules'] or {},
                "error_message": assessment_run['error_message'],
                "started_at": assessment_run['started_at'].isoformat() if assessment_run['started_at'] else None,
                "completed_at": assessment_run['completed_at'].isoformat() if assessment_run['completed_at'] else None
            }
            
            # 构建breakdown数据
            breakdown_data = {}
            if assessment_run['idea_score'] is not None:
                breakdown_data["idea"] = assessment_run['idea_score']
            if assessment_run['ui_score'] is not None:
                breakdown_data["ui"] = assessment_run['ui_score']
            if assessment_run['code_score'] is not None:
                breakdown_data["code"] = assessment_run['code_score']
            
            # 添加详细子维度分数
            if assessment_run['detailed_scores']:
                detailed_scores = assessment_run['detailed_scores']
                if 'idea' in detailed_scores:
                    breakdown_data["idea_detail"] = detailed_scores['idea']
                if 'ui' in detailed_scores:
                    breakdown_data["ui_detail"] = detailed_scores['ui']
                if 'code' in detailed_scores:
                    breakdown_data["code_detail"] = detailed_scores['code']
            
            assessment["breakdown"] = breakdown_data
            
            return assessment
            
        except Exception as e:
            logger.error(f"从数据库获取评估记录失败: {str(e)}")
            raise AssessmentServiceError(f"获取评估记录失败: {str(e)}")
        
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
        try:
            # 从数据库获取评估记录
            assessment_runs = self.db_service.get_student_assessment_runs(
                student_id or "", 
                limit=1000  # 获取足够多的记录
            )
            
            # 转换为前端需要的格式
            processed_assessments = []
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
                
                assessment_data = {
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
                processed_assessments.append(assessment_data)
            
            # 按时间降序排序
            processed_assessments.sort(key=lambda x: x['created_at'], reverse=True)
            
            logger.info(f"📊 从数据库获取评估记录: {len(processed_assessments)} 条")
            return processed_assessments
            
        except Exception as e:
            logger.error(f"从数据库获取评估记录失败: {str(e)}")
            return []
    
    async def _execute_assessment(self, assessment_id: str):
        """
        异步执行评估流程
        """
        try:
            # 从数据库获取评估记录
            assessment_run = self.db_service.get_assessment_run(assessment_id)
            if not assessment_run:
                logger.error(f"📋 ❌ 评估记录不存在: {assessment_id}")
                return
            
            # 更新状态到数据库
            self.db_service.update_assessment_run(assessment_id, {
                'status': 'in_progress',
                'started_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            logger.info(f"📋 🚀 开始执行评估: {assessment_id}")
            
            # 构建评估数据
            evaluation_data = self._prepare_evaluation_data_from_db(assessment_run)
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
            
            # 更新评估状态到数据库
            update_data = {
                'status': 'completed',
                'overall_score': result["overall_score"],
                'idea_score': result["score_breakdown"].idea,
                'ui_score': result["score_breakdown"].ui,
                'code_score': result["score_breakdown"].code,
                'detailed_scores': result.get("detailed_scores", {}),
                'diagnosis': result["diagnoses"],
                'resources': result["resources"],
                'exit_rules': {
                    'pass_status': result["exit_rules"].pass_status,
                    'path_update': result["exit_rules"].path_update,
                    'remedy': result["exit_rules"].remedy
                } if hasattr(result["exit_rules"], 'pass_status') else result["exit_rules"],
                'completed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            self.db_service.update_assessment_run(assessment_id, update_data)
            
            logger.info(f"📋 🎉 评估完成并保存: {assessment_id}, 总分: {result['overall_score']}")
            
            # 🆕 集成学习路径推荐系统（可通过配置开关控制）
            if path_config.enable_path_integration:
                await self._update_learning_path(assessment_id, assessment_run)
            else:
                logger.info(f"📋 ℹ️ 学习路径集成已禁用，跳过路径更新: {assessment_id}")
            
        except Exception as e:
            # 处理评估异常
            logger.error(f"📋 ❌ 评估执行失败: {assessment_id}, 错误: {str(e)}")
            
            try:
                # 更新数据库中的错误状态
                self.db_service.update_assessment_run(assessment_id, {
                    'status': 'failed',
                    'error_message': str(e),
                    'updated_at': datetime.utcnow()
                })
            except Exception as save_error:
                logger.error(f"📋 ❌ 保存错误状态失败: {str(save_error)}")
    
    async def _update_learning_path(self, assessment_id: str, assessment_run):
        """
        🆕 更新学习路径进度
        
        当评估完成后，自动调用学习路径服务来：
        1. 更新学生的节点进度
        2. 根据评估结果推荐下一步路径
        """
        try:
            student_id = assessment_run.student_id
            
            # 从评估结果中推断当前学习的节点
            current_node_id = self._infer_current_node_from_db(assessment_run)
            
            # 构建评估结果数据
            assessment_result = {
                "overall_score": float(assessment_run.overall_score) if assessment_run.overall_score else 0,
                "breakdown": {
                    "idea": float(assessment_run.idea_score) if assessment_run.idea_score else 0,
                    "ui": float(assessment_run.ui_score) if assessment_run.ui_score else 0,
                    "code": float(assessment_run.code_score) if assessment_run.code_score else 0
                },
                "diagnosis": assessment_run.diagnosis or [],
                "exit_rules": assessment_run.exit_rules or {}
            }
            
            # 确定节点状态
            overall_score_val = float(assessment_run.overall_score) if assessment_run.overall_score else 0
            if overall_score_val >= 60:  # 通过门槛
                node_status = NodeStatus.COMPLETED
                logger.info(f"✅ 节点通过: {current_node_id} (得分: {overall_score_val}分 >= 60分)")
            else:
                node_status = NodeStatus.FAILED
                logger.info(f"❌ 节点未通过: {current_node_id} (得分: {overall_score_val}分 < 60分) - 需要降级重修")
            
            logger.info(f"📚🤖 开始更新学习路径: {student_id} -> {current_node_id} -> {node_status.value} (得分: {overall_score_val}分)")
            
            # 更新学生进度
            await self.learning_path_service.update_student_progress(
                student_id=student_id,
                node_id=current_node_id,
                status=node_status,
                assessment_result=assessment_result
            )
            
            # 如果节点完成或失败，都生成路径推荐
            # COMPLETED: 决定升级/保持/进入下一节点
            # FAILED: 决定降级重修或保持难度重修
            if node_status in [NodeStatus.COMPLETED, NodeStatus.FAILED]:
                recommendation = await self.learning_path_service.recommend_next_step(
                    student_id=student_id,
                    assessment_result=assessment_result
                )
                logger.info(f"📚🤖 路径推荐已生成: {student_id} -> {recommendation.recommended_channel.value}通道 -> {recommendation.next_node_id}, 决策: {recommendation.decision.value}")
            
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
    
    def _infer_current_node_from_db(self, assessment_run) -> str:
        """从数据库记录推断当前节点"""
        # 使用节点ID字段，如果没有则使用默认推断
        if assessment_run.node_id:
            return assessment_run.node_id
        return self._default_node_inference()
    
    def _get_task_info(self, node_id: str, channel: str) -> Dict[str, Any]:
        """获取任务信息"""
        try:
            # 从学习路径服务获取任务信息
            learning_path = self.learning_path_service.get_learning_path()
            if not learning_path:
                logger.warning(f"无法获取学习路径，返回空任务信息")
                return {
                    "requirements": [],
                    "deliverables": [],
                    "description": ""
                }
            
            # 查找节点
            current_node = None
            for node in learning_path.nodes:
                if node.id == node_id:
                    current_node = node
                    break
            
            if not current_node:
                logger.warning(f"未找到节点: {node_id}")
                return {
                    "requirements": [],
                    "deliverables": [],
                    "description": ""
                }
            
            # 获取通道任务信息
            from ..models.learning_path import Channel as ChannelEnum
            channel_enum = ChannelEnum[channel]
            channel_task = current_node.channel_tasks.get(channel_enum, {})
            
            task_info = {
                "description": channel_task.get("task", ""),
                "requirements": channel_task.get("requirements", []),
                "deliverables": channel_task.get("deliverables", [])
            }
            
            logger.info(f"✅ 成功获取任务信息: {node_id} -> {channel}")
            logger.info(f"    任务要求: {len(task_info['requirements'])} 项")
            logger.info(f"    提交要求: {len(task_info['deliverables'])} 项")
            return task_info
            
        except Exception as e:
            logger.error(f"获取任务信息失败: {str(e)}")
            return {
                "requirements": [],
                "deliverables": [],
                "description": ""
            }
    
    def _check_deliverables_completeness(self, evaluation_data: Dict[str, Any], 
                                         task_requirements: List[str], 
                                         task_deliverables: List[str]) -> Dict[str, Any]:
        """检查提交材料的完整性"""
        missing_deliverables = []
        has_code = bool(evaluation_data.get("code_repo") or evaluation_data.get("code_snippets"))
        has_ui = bool(evaluation_data.get("ui_images"))
        has_idea = bool(evaluation_data.get("idea_text"))
        
        # 检查常见的提交要求
        for deliverable in task_deliverables:
            deliverable_lower = deliverable.lower()
            
            # 代码相关
            if any(keyword in deliverable_lower for keyword in ["代码", "程序", "实现", "源码", "repository", "repo"]):
                if not has_code:
                    missing_deliverables.append(deliverable)
            
            # UI相关
            elif any(keyword in deliverable_lower for keyword in ["ui", "界面", "设计", "原型", "图片"]):
                if not has_ui:
                    missing_deliverables.append(deliverable)
            
            # 创意相关
            elif any(keyword in deliverable_lower for keyword in ["创意", "想法", "项目描述", "idea"]):
                if not has_idea:
                    missing_deliverables.append(deliverable)
        
        completeness_info = {
            "missing_deliverables": missing_deliverables,
            "has_code": has_code,
            "has_ui": has_ui,
            "has_idea": has_idea,
            "is_complete": len(missing_deliverables) == 0
        }
        
        if missing_deliverables:
            logger.warning(f"⚠️ 提交材料不完整，缺失: {missing_deliverables}")
        else:
            logger.info(f"✅ 提交材料完整")
        
        return completeness_info

    def _prepare_evaluation_data_from_db(self, assessment_run) -> Dict[str, Any]:
        """从数据库记录准备评估数据"""
        logger.info(f"📋 🔍 开始准备评估数据，评估ID: {assessment_run['run_id']}")
        
        # 从关联的提交记录获取详细信息
        submissions = self.db_service.get_submissions_by_assessment_run(assessment_run['run_id'])
        logger.info(f"📋 📊 找到 {len(submissions)} 条提交记录")
        
        # 🔥 获取任务信息
        node_id = assessment_run.get('node_id')
        channel = assessment_run.get('channel')
        task_info = self._get_task_info(node_id, channel)
        logger.info(f"📋 📝 任务信息: {node_id} -> {channel}通道")
        logger.info(f"    任务要求: {task_info.get('requirements', [])}")
        logger.info(f"    提交要求: {task_info.get('deliverables', [])}")
        
        # 构建评估数据
        evaluation_data = {
            # Idea相关数据
            "idea_text": "",
            "project_name": "项目",
            "technical_stack": [],
            "target_users": "用户",
            "core_features": [],
            
            # UI相关数据
            "ui_images": [],
            "design_tool": "",
            "design_system": "",
            "color_palette": [],
            "prototype_url": "",
            
            # 代码相关数据
            "code_repo": "",
            "language": "python",
            "framework": "未指定",
            "lines_of_code": 0,
            "test_coverage": 0.0,
            "code_snippets": [],
            
            # 🔥 新增：任务信息
            "task_requirements": task_info.get('requirements', []),
            "task_deliverables": task_info.get('deliverables', []),
            "task_description": task_info.get('description', ''),
            "node_id": node_id,
            "channel": channel
        }
        
        # 从提交记录中提取数据
        for i, submission in enumerate(submissions):
            logger.info(f"📋 📝 处理第 {i+1} 条提交记录:")
            logger.info(f"    提交ID: {submission['submission_id']}")
            logger.info(f"    提交类型: {submission['submission_type']}")
            logger.info(f"    文件路径: {submission['file_path']}")
            logger.info(f"    创意文本长度: {len(submission['idea_text']) if submission['idea_text'] else 0}")
            logger.info(f"    代码仓库: {submission['code_repo']}")
            logger.info(f"    代码片段数量: {len(submission['code_snippets']) if submission['code_snippets'] else 0}")
            
            if submission['idea_text']:
                evaluation_data["idea_text"] = submission['idea_text']
                logger.info(f"    ✅ 设置创意文本: {submission['idea_text'][:100]}...")
            if submission['ui_images']:
                evaluation_data["ui_images"] = submission['ui_images']
                logger.info(f"    ✅ 设置UI图片: {len(submission['ui_images'])} 张")
            if submission['code_repo']:
                evaluation_data["code_repo"] = submission['code_repo']
                logger.info(f"    ✅ 设置代码仓库: {submission['code_repo']}")
            if submission['code_snippets']:
                evaluation_data["code_snippets"] = submission['code_snippets']
                logger.info(f"    ✅ 设置代码片段: {len(submission['code_snippets'])} 个文件")
                if isinstance(submission['code_snippets'], list):
                    for i, content in enumerate(submission['code_snippets'][:2]):  # 只显示前2个文件
                        logger.info(f"      文件 {i+1}: (长度: {len(content)})")
                elif isinstance(submission['code_snippets'], dict):
                    for file_name, content in list(submission['code_snippets'].items())[:2]:  # 只显示前2个文件
                        logger.info(f"      文件: {file_name} (长度: {len(content)})")
        
        logger.info(f"📋 📊 最终评估数据:")
        logger.info(f"    创意文本: {evaluation_data['idea_text'][:50] if evaluation_data['idea_text'] else 'None'}...")
        logger.info(f"    代码仓库: {evaluation_data['code_repo']}")
        logger.info(f"    代码片段数量: {len(evaluation_data['code_snippets'])}")
        if evaluation_data['code_snippets']:
            if isinstance(evaluation_data['code_snippets'], list):
                logger.info(f"    代码片段类型: 列表 ({len(evaluation_data['code_snippets'])} 个)")
            elif isinstance(evaluation_data['code_snippets'], dict):
                logger.info(f"    代码片段文件: {list(evaluation_data['code_snippets'].keys())}")
        else:
            logger.info(f"    代码片段文件: None")
        
        # 🔥 检查提交材料完整性
        completeness_info = self._check_deliverables_completeness(
            evaluation_data, 
            task_info.get('requirements', []),
            task_info.get('deliverables', [])
        )
        
        # 将完整性信息添加到评估数据中
        evaluation_data["completeness_info"] = completeness_info
        
        # 如果有缺失的材料，记录警告
        if not completeness_info["is_complete"]:
            logger.warning(f"⚠️⚠️⚠️ 提交材料不完整！缺失项: {completeness_info['missing_deliverables']}")
            logger.warning(f"    存在代码: {completeness_info['has_code']}")
            logger.warning(f"    存在UI: {completeness_info['has_ui']}")
            logger.warning(f"    存在创意: {completeness_info['has_idea']}")
        
        return evaluation_data

    def _prepare_evaluation_data(self, assessment: Assessment) -> Dict[str, Any]:
        """准备评估数据（兼容性方法）"""
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
        # 从数据库获取评估记录
        assessment_run = self.db_service.get_assessment_run(assessment_id)
        if not assessment_run:
            raise AssessmentServiceError(f"评估记录不存在: {assessment_id}")
        
        if assessment_run['status'] != 'completed':
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