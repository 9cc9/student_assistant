"""学习路径推荐服务核心实现"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import json

from ..storage.file_storage import get_storage
from ..models.learning_path import (
    LearningPath, PathNode, Channel, NodeStatus, PathDecision,
    StudentPathProgress, PathRecommendation, CheckpointRule
)
from ..models.student import StudentProfile, LearningLevel, LearningStyle

logger = logging.getLogger(__name__)


class LearningPathService:
    """学习路径推荐服务类，负责管理个性化学习路径"""
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.storage = get_storage()
            self._initialized = True
            
        # 加载或初始化路径数据
        if not hasattr(self, 'learning_paths'):
            self.learning_paths = {}
            self.student_progresses = {}
            self._init_default_course_path()
            logger.info(f"📚 LearningPathService 已初始化")
    
    def _init_default_course_path(self):
        """初始化默认的课程学习路径"""
        # 定义课程的7个固定节点
        course_nodes = [
            self._create_node("api_calling", "API调用", "学习如何调用各种API接口", 1),
            self._create_node("model_deployment", "模型部署", "学习如何部署AI模型", 2),
            self._create_node("no_code_ai", "零代码配置AI应用", "使用无代码平台构建AI应用", 3),
            self._create_node("rag_system", "RAG系统", "构建检索增强生成系统", 4),
            self._create_node("ui_design", "UI设计", "设计用户界面", 5),
            self._create_node("frontend_dev", "前端开发", "开发前端应用", 6),
            self._create_node("backend_dev", "后端开发", "开发后端服务", 7),
        ]
        
        # 创建默认学习路径
        default_path = LearningPath(
            id="default_course_path",
            name="基于大模型的个性化生活助手开发课程",
            description="从API调用到完整应用开发的全流程学习路径",
            nodes=course_nodes,
            target_audience=["本科生", "初学者", "有基础的开发者"],
            prerequisites_knowledge=["基本编程概念", "Python基础"],
            learning_outcomes=[
                "掌握大模型API调用技能", 
                "能够独立部署AI模型",
                "具备完整的前后端开发能力",
                "能够构建RAG应用系统"
            ]
        )
        
        self.learning_paths["default_course_path"] = default_path
        logger.info(f"📚 默认课程路径已创建，包含 {len(course_nodes)} 个节点")
    
    def _create_node(self, node_id: str, name: str, description: str, order: int) -> PathNode:
        """创建学习节点"""
        # 根据节点类型定义A/B/C通道任务
        channel_tasks = self._get_channel_tasks_for_node(node_id)
        estimated_hours = self._get_estimated_hours_for_node(node_id)
        difficulty_level = self._get_difficulty_level_for_node(node_id)
        
        # 设置前置依赖
        prerequisites = []
        if order > 1:
            prev_nodes = [
                "api_calling", "model_deployment", "no_code_ai", 
                "rag_system", "ui_design", "frontend_dev", "backend_dev"
            ]
            if order <= len(prev_nodes):
                prerequisites = [prev_nodes[order - 2]]  # 前一个节点作为依赖
        
        # 创建门槛卡
        checkpoint = CheckpointRule(
            checkpoint_id=f"{node_id}_checkpoint",
            must_pass=self._get_checkpoint_requirements(node_id),
            evidence=self._get_checkpoint_evidence(node_id),
            auto_grade=self._get_auto_grade_rules(node_id)
        )
        
        # 补救资源
        remedy_resources = self._get_remedy_resources(node_id)
        
        return PathNode(
            id=node_id,
            name=name,
            description=description,
            order=order,
            channel_tasks=channel_tasks,
            prerequisites=prerequisites,
            checkpoint=checkpoint,
            remedy_resources=remedy_resources,
            estimated_hours=estimated_hours,
            difficulty_level=difficulty_level
        )
    
    def _get_channel_tasks_for_node(self, node_id: str) -> Dict[Channel, Dict[str, Any]]:
        """获取节点的A/B/C通道任务定义"""
        tasks_mapping = {
            "api_calling": {
                Channel.A: {
                    "task": "用SDK完成3个API调用",
                    "requirements": ["成功调用OpenAI API", "处理基本错误", "输出结果"],
                    "deliverables": ["调用代码", "运行截图", "简单报告"]
                },
                Channel.B: {
                    "task": "手写HTTP并处理鉴权/限流",
                    "requirements": ["实现HTTP请求", "处理API鉴权", "实现错误重试", "限流控制"],
                    "deliverables": ["完整代码", "错误处理机制", "测试用例"]
                },
                Channel.C: {
                    "task": "封装可复用SDK并发布包",
                    "requirements": ["SDK架构设计", "完整单元测试", "文档编写", "发布到PyPI"],
                    "deliverables": ["SDK包", "完整文档", "使用示例", "PyPI链接"]
                }
            },
            "model_deployment": {
                Channel.A: {
                    "task": "Ollama本地拉起模型",
                    "requirements": ["安装Ollama", "成功运行模型", "基本调用测试"],
                    "deliverables": ["部署截图", "调用代码", "测试结果"]
                },
                Channel.B: {
                    "task": "Docker化并开放REST接口",
                    "requirements": ["编写Dockerfile", "构建镜像", "REST API", "接口文档"],
                    "deliverables": ["Docker镜像", "API文档", "部署脚本"]
                },
                Channel.C: {
                    "task": "GPU/并发优化与压测",
                    "requirements": ["GPU加速配置", "并发处理", "性能测试", "负载均衡"],
                    "deliverables": ["优化报告", "压测结果", "部署方案"]
                }
            },
            "no_code_ai": {
                Channel.A: {
                    "task": "Dify搭建基础Flow",
                    "requirements": ["创建基础对话Flow", "连接LLM", "测试功能"],
                    "deliverables": ["Flow截图", "测试对话", "功能演示"]
                },
                Channel.B: {
                    "task": "引入工具调用与变量",
                    "requirements": ["集成工具调用", "变量管理", "条件分支", "复杂Flow"],
                    "deliverables": ["复杂Flow", "工具集成", "变量配置"]
                },
                Channel.C: {
                    "task": "自定义插件扩展",
                    "requirements": ["开发自定义插件", "API集成", "插件文档", "分享发布"],
                    "deliverables": ["插件代码", "集成演示", "使用文档"]
                }
            },
            "rag_system": {
                Channel.A: {
                    "task": "用LangChain现成模块",
                    "requirements": ["文档加载", "向量存储", "基础检索", "简单问答"],
                    "deliverables": ["RAG系统", "查询演示", "简单UI"]
                },
                Channel.B: {
                    "task": "手搓Embedding+FAISS",
                    "requirements": ["自实现Embedding", "FAISS索引", "检索算法", "相关性排序"],
                    "deliverables": ["检索系统", "性能测试", "对比分析"]
                },
                Channel.C: {
                    "task": "加入重排序/多向量检索",
                    "requirements": ["重排序算法", "多向量融合", "检索优化", "评估系统"],
                    "deliverables": ["高级检索系统", "性能报告", "优化方案"]
                }
            },
            "ui_design": {
                Channel.A: {
                    "task": "使用模板快速搭建",
                    "requirements": ["选择合适模板", "基础修改", "颜色调整", "内容替换"],
                    "deliverables": ["设计稿", "色彩方案", "组件库"]
                },
                Channel.B: {
                    "task": "遵循设计规范进行定制",
                    "requirements": ["遵循Material Design", "可访问性设计", "交互规范", "用户测试"],
                    "deliverables": ["设计系统", "原型图", "用户测试报告"]
                },
                Channel.C: {
                    "task": "实现响应式布局与交互优化",
                    "requirements": ["响应式设计", "高级交互", "动效设计", "性能优化"],
                    "deliverables": ["完整设计系统", "交互演示", "设计文档"]
                }
            },
            "frontend_dev": {
                Channel.A: {
                    "task": "使用框架模板二开",
                    "requirements": ["框架模板使用", "基础组件", "简单交互", "基本部署"],
                    "deliverables": ["前端应用", "功能演示", "部署链接"]
                },
                Channel.B: {
                    "task": "从零搭建React/Vue应用",
                    "requirements": ["项目搭建", "组件开发", "状态管理", "路由配置"],
                    "deliverables": ["完整应用", "代码仓库", "技术文档"]
                },
                Channel.C: {
                    "task": "集成状态管理与性能优化",
                    "requirements": ["Redux/Vuex", "性能优化", "代码分割", "PWA特性"],
                    "deliverables": ["高级应用", "性能报告", "优化方案"]
                }
            },
            "backend_dev": {
                Channel.A: {
                    "task": "使用FastAPI/Flask模板",
                    "requirements": ["API模板使用", "基础路由", "简单数据库", "基本部署"],
                    "deliverables": ["后端服务", "API文档", "部署演示"]
                },
                Channel.B: {
                    "task": "从零搭建RESTful API",
                    "requirements": ["API设计", "数据库设计", "认证鉴权", "错误处理"],
                    "deliverables": ["完整API服务", "数据库设计", "接口文档"]
                },
                Channel.C: {
                    "task": "集成MCP/Agent框架与权限/日志",
                    "requirements": ["Agent框架集成", "复杂权限系统", "完整日志", "监控系统"],
                    "deliverables": ["企业级后端", "监控报告", "运维方案"]
                }
            }
        }
        
        return tasks_mapping.get(node_id, {
            Channel.A: {"task": "基础任务", "requirements": ["基础要求"], "deliverables": ["基础交付"]},
            Channel.B: {"task": "标准任务", "requirements": ["标准要求"], "deliverables": ["标准交付"]},
            Channel.C: {"task": "挑战任务", "requirements": ["挑战要求"], "deliverables": ["挑战交付"]}
        })
    
    def _get_estimated_hours_for_node(self, node_id: str) -> Dict[Channel, int]:
        """获取节点的预估学习时长"""
        hours_mapping = {
            "api_calling": {Channel.A: 4, Channel.B: 8, Channel.C: 16},
            "model_deployment": {Channel.A: 6, Channel.B: 12, Channel.C: 20},
            "no_code_ai": {Channel.A: 3, Channel.B: 6, Channel.C: 12},
            "rag_system": {Channel.A: 8, Channel.B: 16, Channel.C: 24},
            "ui_design": {Channel.A: 6, Channel.B: 12, Channel.C: 18},
            "frontend_dev": {Channel.A: 10, Channel.B: 20, Channel.C: 30},
            "backend_dev": {Channel.A: 12, Channel.B: 24, Channel.C: 36}
        }
        return hours_mapping.get(node_id, {Channel.A: 4, Channel.B: 8, Channel.C: 12})
    
    def _get_difficulty_level_for_node(self, node_id: str) -> Dict[Channel, int]:
        """获取节点的难度等级 (1-10)"""
        difficulty_mapping = {
            "api_calling": {Channel.A: 3, Channel.B: 6, Channel.C: 9},
            "model_deployment": {Channel.A: 4, Channel.B: 7, Channel.C: 9},
            "no_code_ai": {Channel.A: 2, Channel.B: 4, Channel.C: 7},
            "rag_system": {Channel.A: 5, Channel.B: 8, Channel.C: 10},
            "ui_design": {Channel.A: 3, Channel.B: 6, Channel.C: 8},
            "frontend_dev": {Channel.A: 4, Channel.B: 7, Channel.C: 9},
            "backend_dev": {Channel.A: 5, Channel.B: 8, Channel.C: 10}
        }
        return difficulty_mapping.get(node_id, {Channel.A: 3, Channel.B: 6, Channel.C: 9})
    
    def _get_checkpoint_requirements(self, node_id: str) -> List[str]:
        """获取门槛卡要求"""
        requirements_mapping = {
            "api_calling": ["能成功调用API", "能处理基本错误", "理解API限流机制"],
            "model_deployment": ["能本地部署模型", "能配置基本参数", "理解模型推理过程"],
            "no_code_ai": ["能创建AI应用Flow", "能配置基本功能", "能调试应用逻辑"],
            "rag_system": ["能独立构建索引", "能解释召回与精排差异", "能评估检索效果"],
            "ui_design": ["遵循设计规范", "满足可访问性要求", "通过用户测试"],
            "frontend_dev": ["功能完整可用", "代码规范良好", "性能达标"],
            "backend_dev": ["API接口完整", "数据安全可靠", "错误处理完善"]
        }
        return requirements_mapping.get(node_id, ["完成基础要求", "通过质量检查"])
    
    def _get_checkpoint_evidence(self, node_id: str) -> List[str]:
        """获取门槛卡证据要求"""
        evidence_mapping = {
            "api_calling": ["代码仓库链接", "运行截图", "测试报告"],
            "model_deployment": ["部署文档", "运行演示", "性能测试"],
            "no_code_ai": ["应用链接", "功能演示视频", "配置说明"],
            "rag_system": ["系统演示", "性能评估报告", "技术说明文档"],
            "ui_design": ["设计稿", "原型链接", "用户测试报告"],
            "frontend_dev": ["在线演示", "代码仓库", "技术文档"],
            "backend_dev": ["API文档", "部署说明", "测试用例"]
        }
        return evidence_mapping.get(node_id, ["仓库链接", "演示视频", "说明文档"])
    
    def _get_auto_grade_rules(self, node_id: str) -> Dict[str, Any]:
        """获取自动评分规则"""
        rules_mapping = {
            "api_calling": {
                "success_rate": 0.9,
                "response_time_ms": 2000,
                "error_handling": True
            },
            "model_deployment": {
                "deployment_success": True,
                "response_time_ms": 5000,
                "memory_usage_mb": 2048
            },
            "rag_system": {
                "unit_test_coverage": 0.8,
                "latency_ms_at_k5": 800,
                "relevance_score": 0.7
            },
            "ui_design": {
                "accessibility_score": 0.8,
                "performance_score": 0.7,
                "design_consistency": True
            },
            "frontend_dev": {
                "lighthouse_score": 80,
                "test_coverage": 0.7,
                "build_success": True
            },
            "backend_dev": {
                "api_test_pass_rate": 0.9,
                "security_scan_pass": True,
                "performance_benchmark": True
            }
        }
        return rules_mapping.get(node_id, {"basic_completion": True})
    
    def _get_remedy_resources(self, node_id: str) -> Dict[str, List[str]]:
        """获取补救资源"""
        resources_mapping = {
            "api_calling": {
                "微课": ["API调用基础", "错误处理最佳实践", "限流与重试机制"],
                "引导题": ["练习API调用", "处理不同错误类型", "实现指数退避"],
                "对照示例": ["标准API调用代码", "错误处理示例", "SDK封装示例"]
            },
            "model_deployment": {
                "微课": ["模型部署基础", "Docker容器化", "性能优化技巧"],
                "引导题": ["本地部署练习", "容器化实践", "性能测试"],
                "对照示例": ["部署脚本模板", "Dockerfile示例", "监控配置"]
            },
            "rag_system": {
                "微课": ["向量数据库原理", "检索算法优化", "评估方法"],
                "引导题": ["构建简单索引", "实现检索排序", "评估检索质量"],
                "对照示例": ["RAG系统架构", "检索优化代码", "评估脚本"]
            }
        }
        return resources_mapping.get(node_id, {
            "微课": ["基础概念讲解"],
            "引导题": ["实践练习"],
            "对照示例": ["参考代码"]
        })
    
    async def create_student_profile(
        self, 
        student_id: str, 
        diagnostic_results: Dict[str, Any]
    ) -> StudentProfile:
        """基于入学诊断结果创建学生画像"""
        
        # 解析诊断结果
        level = self._determine_learning_level(diagnostic_results)
        weak_skills = self._identify_weak_skills(diagnostic_results)
        interests = diagnostic_results.get("interests", [])
        learning_style = self._determine_learning_style(diagnostic_results)
        time_budget = diagnostic_results.get("time_budget_hours_per_week", 6)
        goals = diagnostic_results.get("goals", [])
        
        profile = StudentProfile(
            student_id=student_id,
            level=level,
            weak_skills=weak_skills,
            interests=interests,
            learning_style=learning_style,
            time_budget_hours_per_week=time_budget,
            goals=goals,
            mastery_scores={},
            frustration_level=0.0,
            retry_count=0
        )
        
        logger.info(f"📚 学生画像已创建: {student_id}, 水平: {level.value}")
        return profile
    
    def _determine_learning_level(self, diagnostic_results: Dict[str, Any]) -> LearningLevel:
        """根据诊断结果确定学习水平"""
        concept_score = diagnostic_results.get("concept_score", 0)
        coding_score = diagnostic_results.get("coding_score", 0)
        tool_familiarity = diagnostic_results.get("tool_familiarity", 0)
        
        average_score = (concept_score + coding_score + tool_familiarity) / 3
        
        if average_score >= 85:
            return LearningLevel.L3  # 高级/竞赛型
        elif average_score >= 70:
            return LearningLevel.L2  # 中级
        elif average_score >= 50:
            return LearningLevel.L1  # 初级
        else:
            return LearningLevel.L0  # 零基础
    
    def _identify_weak_skills(self, diagnostic_results: Dict[str, Any]) -> List[str]:
        """识别薄弱技能"""
        weak_skills = []
        skill_scores = diagnostic_results.get("skill_scores", {})
        
        for skill, score in skill_scores.items():
            if score < 60:  # 60分以下认为是薄弱技能
                weak_skills.append(skill)
        
        return weak_skills
    
    def _determine_learning_style(self, diagnostic_results: Dict[str, Any]) -> LearningStyle:
        """确定学习风格"""
        style_preference = diagnostic_results.get("learning_style_preference", "examples_first")
        
        style_mapping = {
            "examples_first": LearningStyle.EXAMPLES_FIRST,
            "theory_first": LearningStyle.THEORY_FIRST,
            "hands_on": LearningStyle.HANDS_ON,
            "visual": LearningStyle.VISUAL
        }
        
        return style_mapping.get(style_preference, LearningStyle.EXAMPLES_FIRST)
    
    async def initialize_student_path(
        self, 
        student_id: str, 
        profile: StudentProfile
    ) -> StudentPathProgress:
        """为学生初始化学习路径进度"""
        
        # 根据学生水平确定起始通道
        initial_channel = self._determine_initial_channel(profile.level)
        
        # 创建进度跟踪
        progress = StudentPathProgress(
            student_id=student_id,
            current_node_id="api_calling",  # 从第一个节点开始
            current_channel=initial_channel,
            node_statuses={"api_calling": NodeStatus.AVAILABLE},
            completed_nodes=[],
            mastery_scores={},
            frustration_level=0.0,
            retry_counts={},
            started_at=datetime.now()
        )
        
        # 根据薄弱技能初始化掌握度分数
        for skill in profile.weak_skills:
            progress.mastery_scores[skill] = 0.3  # 薄弱技能起始分数较低
        
        # 存储进度
        self.student_progresses[student_id] = progress
        
        logger.info(f"📚 学生学习路径已初始化: {student_id}, 起始通道: {initial_channel.value}")
        return progress
    
    def _determine_initial_channel(self, level: LearningLevel) -> Channel:
        """根据学习水平确定初始通道"""
        channel_mapping = {
            LearningLevel.L0: Channel.A,  # 零基础从A通道开始
            LearningLevel.L1: Channel.B,  # 初级从B通道开始
            LearningLevel.L2: Channel.B,  # 中级从B通道开始
            LearningLevel.L3: Channel.C   # 高级从C通道开始
        }
        return channel_mapping.get(level, Channel.B)
    
    async def recommend_next_step(
        self, 
        student_id: str, 
        assessment_result: Optional[Dict[str, Any]] = None
    ) -> PathRecommendation:
        """推荐下一步学习路径"""
        
        progress = self.student_progresses.get(student_id)
        if not progress:
            raise ValueError(f"学生学习进度不存在: {student_id}")
        
        current_node_id = progress.current_node_id
        current_channel = progress.current_channel
        
        # 如果有评估结果，根据结果决定路径调整
        if assessment_result:
            decision = self._make_path_decision(progress, assessment_result)
        else:
            # 没有评估结果，保持当前通道继续下一节点
            decision = PathDecision.KEEP
        
        # 确定推荐通道
        recommended_channel = self._determine_recommended_channel(current_channel, decision)
        
        # 确定下一个节点
        next_node_id = self._get_next_node(current_node_id, progress.completed_nodes)
        
        # 生成推荐理由
        reasoning, trigger_factors = self._generate_recommendation_reasoning(
            progress, assessment_result, decision
        )
        
        # 生成备选方案
        alternatives = self._generate_alternative_options(current_node_id, progress)
        
        # 生成脚手架资源
        scaffold_resources = self._generate_scaffold_resources(decision, next_node_id)
        
        # 估算完成时间
        estimated_time = self._estimate_completion_time(next_node_id, recommended_channel)
        
        recommendation = PathRecommendation(
            student_id=student_id,
            recommended_channel=recommended_channel,
            next_node_id=next_node_id,
            decision=decision,
            reasoning=reasoning,
            trigger_factors=trigger_factors,
            alternative_options=alternatives,
            scaffold_resources=scaffold_resources,
            estimated_completion_time=estimated_time
        )
        
        logger.info(f"📚 路径推荐已生成: {student_id}, 推荐: {next_node_id}({recommended_channel.value}), 决策: {decision.value}")
        return recommendation
    
    def _make_path_decision(
        self, 
        progress: StudentPathProgress, 
        assessment_result: Dict[str, Any]
    ) -> PathDecision:
        """基于评估结果做出路径决策"""
        
        overall_score = assessment_result.get("overall_score", 0)
        mastery = overall_score / 100.0  # 转换为0-1范围
        
        # 更新掌握度和挫败感
        frustration = progress.frustration_level
        retry_count = progress.retry_counts.get(progress.current_node_id, 0)
        
        # 应用决策逻辑
        if mastery > 0.85 and frustration < 0.2:
            return PathDecision.UPGRADE  # 升级通道
        elif mastery < 0.60 or retry_count >= 3:
            return PathDecision.DOWNGRADE  # 降级并提供脚手架
        else:
            return PathDecision.KEEP  # 保持当前通道
    
    def _determine_recommended_channel(
        self, 
        current_channel: Channel, 
        decision: PathDecision
    ) -> Channel:
        """根据决策确定推荐通道"""
        
        if decision == PathDecision.UPGRADE:
            if current_channel == Channel.A:
                return Channel.B
            elif current_channel == Channel.B:
                return Channel.C
            else:
                return Channel.C  # 已经是最高通道
        elif decision == PathDecision.DOWNGRADE:
            if current_channel == Channel.C:
                return Channel.B
            elif current_channel == Channel.B:
                return Channel.A
            else:
                return Channel.A  # 已经是最低通道
        else:
            return current_channel  # 保持当前通道
    
    def _get_next_node(self, current_node_id: str, completed_nodes: List[str]) -> str:
        """获取下一个学习节点"""
        node_sequence = [
            "api_calling", "model_deployment", "no_code_ai", 
            "rag_system", "ui_design", "frontend_dev", "backend_dev"
        ]
        
        try:
            current_index = node_sequence.index(current_node_id)
            if current_index < len(node_sequence) - 1:
                return node_sequence[current_index + 1]
            else:
                return current_node_id  # 已经是最后一个节点
        except ValueError:
            # 当前节点不在序列中，返回第一个未完成的节点
            for node_id in node_sequence:
                if node_id not in completed_nodes:
                    return node_id
            return node_sequence[0]  # 默认返回第一个节点
    
    def _generate_recommendation_reasoning(
        self,
        progress: StudentPathProgress,
        assessment_result: Optional[Dict[str, Any]],
        decision: PathDecision
    ) -> tuple[str, Dict[str, Any]]:
        """生成推荐理由和触发因子"""
        
        trigger_factors = {
            "current_node": progress.current_node_id,
            "current_channel": progress.current_channel.value,
            "frustration_level": progress.frustration_level,
            "retry_count": progress.retry_counts.get(progress.current_node_id, 0)
        }
        
        if assessment_result:
            overall_score = assessment_result.get("overall_score", 0)
            trigger_factors["overall_score"] = overall_score
            trigger_factors["mastery_level"] = overall_score / 100.0
        
        # 生成推荐理由
        if decision == PathDecision.UPGRADE:
            reasoning = f"基于优秀的评估表现（评分: {trigger_factors.get('overall_score', '良好')}），建议升级到更具挑战性的通道，以充分发挥学习潜能。"
        elif decision == PathDecision.DOWNGRADE:
            reasoning = f"考虑到当前掌握度（{trigger_factors.get('mastery_level', 0.5):.1%}）和重试次数（{trigger_factors['retry_count']}次），建议降级通道并提供额外支持，确保学习效果。"
        else:
            reasoning = "当前学习进展良好，建议保持现有通道继续学习，稳步推进课程进度。"
        
        return reasoning, trigger_factors
    
    def _generate_alternative_options(
        self, 
        current_node_id: str, 
        progress: StudentPathProgress
    ) -> List[Dict[str, Any]]:
        """生成备选学习方案"""
        
        alternatives = []
        
        # 通道切换选项
        for channel in [Channel.A, Channel.B, Channel.C]:
            if channel != progress.current_channel:
                alternatives.append({
                    "option": f"切换到{channel.value}通道",
                    "description": self._get_channel_description(channel),
                    "estimated_hours": self._get_estimated_hours_for_node(current_node_id)[channel],
                    "difficulty": self._get_difficulty_level_for_node(current_node_id)[channel]
                })
        
        # 补救学习选项
        alternatives.append({
            "option": "补救学习路径",
            "description": "通过微课和引导题强化薄弱环节",
            "estimated_hours": 4,
            "difficulty": 2
        })
        
        return alternatives
    
    def _get_channel_description(self, channel: Channel) -> str:
        """获取通道描述"""
        descriptions = {
            Channel.A: "基础保底通道，注重基础概念掌握和实践入门",
            Channel.B: "标准实践通道，涵盖主流技能和完整项目体验",
            Channel.C: "挑战拓展通道，追求工程化实践和高阶技能"
        }
        return descriptions[channel]
    
    def _generate_scaffold_resources(self, decision: PathDecision, node_id: str) -> List[str]:
        """生成脚手架资源"""
        
        if decision == PathDecision.DOWNGRADE:
            remedy_resources = self._get_remedy_resources(node_id)
            scaffold_resources = []
            
            for category, resources in remedy_resources.items():
                scaffold_resources.extend(resources)
            
            return scaffold_resources
        
        return []
    
    def _estimate_completion_time(self, node_id: str, channel: Channel) -> int:
        """估算完成时间（小时）"""
        estimated_hours = self._get_estimated_hours_for_node(node_id)
        return estimated_hours[channel]
    
    async def update_student_progress(
        self,
        student_id: str,
        node_id: str,
        status: NodeStatus,
        assessment_result: Optional[Dict[str, Any]] = None
    ):
        """更新学生学习进度"""
        
        progress = self.student_progresses.get(student_id)
        if not progress:
            raise ValueError(f"学生学习进度不存在: {student_id}")
        
        # 更新节点状态
        progress.node_statuses[node_id] = status
        progress.last_activity_at = datetime.now()
        progress.updated_at = datetime.now()
        
        # 如果节点完成，更新完成列表
        if status == NodeStatus.COMPLETED:
            if node_id not in progress.completed_nodes:
                progress.completed_nodes.append(node_id)
            
            # 解锁下一个节点
            next_node_id = self._get_next_node(node_id, progress.completed_nodes)
            if next_node_id and next_node_id != node_id:
                progress.node_statuses[next_node_id] = NodeStatus.AVAILABLE
                progress.current_node_id = next_node_id
        
        # 更新掌握度分数和挫败感
        if assessment_result:
            overall_score = assessment_result.get("overall_score", 0)
            progress.mastery_scores[node_id] = overall_score / 100.0
            
            # 根据评估结果调整挫败感
            if overall_score < 60:
                progress.frustration_level = min(1.0, progress.frustration_level + 0.1)
                progress.retry_counts[node_id] = progress.retry_counts.get(node_id, 0) + 1
            else:
                progress.frustration_level = max(0.0, progress.frustration_level - 0.05)
        
        logger.info(f"📚 学生进度已更新: {student_id}, 节点: {node_id}, 状态: {status.value}")
    
    def get_student_progress(self, student_id: str) -> Optional[StudentPathProgress]:
        """获取学生学习进度"""
        return self.student_progresses.get(student_id)
    
    def get_learning_path(self, path_id: str = "default_course_path") -> Optional[LearningPath]:
        """获取学习路径"""
        return self.learning_paths.get(path_id)
    
    def get_available_paths(self) -> List[Dict[str, Any]]:
        """获取所有可用的学习路径"""
        paths = []
        for path_id, path in self.learning_paths.items():
            paths.append({
                "id": path_id,
                "name": path.name,
                "description": path.description,
                "node_count": len(path.nodes),
                "target_audience": path.target_audience,
                "prerequisites": path.prerequisites_knowledge,
                "outcomes": path.learning_outcomes
            })
        return paths


class LearningPathServiceError(Exception):
    """学习路径服务错误"""
    pass
