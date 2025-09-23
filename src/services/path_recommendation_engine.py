"""路径推荐引擎 - 基于AI的个性化学习路径推荐"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import asdict

from ..models.learning_path import Channel, PathDecision, NodeStatus
from ..models.student import StudentProfile, LearningLevel, LearningStyle

logger = logging.getLogger(__name__)


class PathRecommendationEngine:
    """
    路径推荐引擎
    
    基于学生画像、学习行为数据和评估结果，使用机器学习算法
    推荐最适合的学习路径和通道选择。
    """
    
    def __init__(self):
        self.weights = self._init_recommendation_weights()
        self.channel_difficulty_map = {
            Channel.A: 1.0,  # 基础保底
            Channel.B: 1.2,  # 标准实践  
            Channel.C: 1.5   # 挑战拓展
        }
        logger.info("🤖 路径推荐引擎已初始化")
    
    def _init_recommendation_weights(self) -> Dict[str, float]:
        """初始化推荐权重配置"""
        return {
            # 学习水平权重
            "learning_level": 0.3,
            
            # 历史表现权重
            "mastery_score": 0.25,
            "frustration_level": 0.15,
            "retry_count": 0.1,
            
            # 时间管理权重
            "time_budget": 0.1,
            "study_pace": 0.05,
            
            # 兴趣匹配权重  
            "interest_alignment": 0.05
        }
    
    async def recommend_initial_path(
        self, 
        student_profile: StudentProfile,
        diagnostic_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        为新学生推荐初始学习路径
        
        Args:
            student_profile: 学生画像
            diagnostic_results: 入学诊断结果
            
        Returns:
            初始路径推荐结果
        """
        
        # 基于学习水平确定起始通道
        initial_channel = self._determine_initial_channel(student_profile.level)
        
        # 基于薄弱技能调整路径策略
        weak_skill_strategy = self._analyze_weak_skills(student_profile.weak_skills)
        
        # 基于时间预算调整学习节奏
        pace_adjustment = self._calculate_pace_adjustment(
            student_profile.time_budget_hours_per_week
        )
        
        # 基于学习风格个性化推荐
        style_recommendations = self._get_style_based_recommendations(
            student_profile.learning_style
        )
        
        # 基于兴趣匹配优化节点重点
        interest_focus = self._analyze_interest_focus(student_profile.interests)
        
        recommendation = {
            "student_id": student_profile.student_id,
            "recommended_channel": initial_channel,
            "starting_node": "api_calling",
            "learning_strategy": {
                "initial_channel": initial_channel.value,
                "weak_skill_focus": weak_skill_strategy,
                "pace_adjustment": pace_adjustment,
                "style_adaptation": style_recommendations,
                "interest_priorities": interest_focus
            },
            "estimated_timeline": self._estimate_course_timeline(
                initial_channel, pace_adjustment
            ),
            "recommended_resources": self._get_initial_resources(student_profile),
            "monitoring_points": self._define_monitoring_checkpoints(),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"🤖 初始路径推荐已生成: {student_profile.student_id} -> {initial_channel.value}通道")
        return recommendation
    
    def _determine_initial_channel(self, level: LearningLevel) -> Channel:
        """根据学习水平确定初始通道"""
        channel_map = {
            LearningLevel.L0: Channel.A,  # 零基础 -> 基础保底
            LearningLevel.L1: Channel.B,  # 初级 -> 标准实践 
            LearningLevel.L2: Channel.B,  # 中级 -> 标准实践
            LearningLevel.L3: Channel.C   # 高级 -> 挑战拓展
        }
        return channel_map.get(level, Channel.B)
    
    def _analyze_weak_skills(self, weak_skills: List[str]) -> Dict[str, Any]:
        """分析薄弱技能，制定强化策略"""
        
        # 将薄弱技能分类
        skill_categories = {
            "programming": ["Python基础", "编程逻辑", "调试技能"],
            "tools": ["Git", "Docker", "IDE使用"],
            "concepts": ["HTTP协议", "API设计", "数据库原理"],
            "frameworks": ["Web框架", "前端框架", "AI框架"]
        }
        
        weak_categories = []
        for category, skills in skill_categories.items():
            if any(skill in weak_skills for skill in skills):
                weak_categories.append(category)
        
        # 基于薄弱技能类型制定策略
        strategy = {
            "focus_areas": weak_categories,
            "extra_practice_needed": len(weak_skills) > 3,
            "suggested_prep_time": min(len(weak_skills) * 2, 10),  # 最多10小时预习
            "remedial_resources": self._map_skills_to_resources(weak_skills)
        }
        
        return strategy
    
    def _map_skills_to_resources(self, weak_skills: List[str]) -> List[str]:
        """将薄弱技能映射到补救资源"""
        resource_map = {
            "Python基础": ["Python入门课程", "基础语法练习"],
            "Git": ["Git基础教程", "版本控制实践"],
            "HTTP协议": ["HTTP协议详解", "Web基础概念"],
            "调试技能": ["调试技巧课程", "错误定位方法"]
        }
        
        resources = []
        for skill in weak_skills:
            if skill in resource_map:
                resources.extend(resource_map[skill])
        
        return list(set(resources))  # 去重
    
    def _calculate_pace_adjustment(self, time_budget: int) -> Dict[str, Any]:
        """根据时间预算计算学习节奏调整"""
        
        # 标准时间预算为每周6小时
        standard_budget = 6
        pace_ratio = time_budget / standard_budget
        
        if pace_ratio <= 0.5:
            pace_level = "慢速"
            timeline_multiplier = 2.0
            suggestion = "建议延长学习周期，重点关注基础掌握"
        elif pace_ratio <= 0.8:
            pace_level = "标准"  
            timeline_multiplier = 1.2
            suggestion = "按标准进度学习，适当增加练习时间"
        elif pace_ratio <= 1.2:
            pace_level = "正常"
            timeline_multiplier = 1.0
            suggestion = "按正常进度推进课程"
        else:
            pace_level = "快速"
            timeline_multiplier = 0.8
            suggestion = "可以适当加快进度，增加挑战性内容"
        
        return {
            "pace_level": pace_level,
            "timeline_multiplier": timeline_multiplier,
            "weekly_hours": time_budget,
            "suggestion": suggestion
        }
    
    def _get_style_based_recommendations(self, style: LearningStyle) -> Dict[str, Any]:
        """根据学习风格提供个性化建议"""
        
        style_strategies = {
            LearningStyle.EXAMPLES_FIRST: {
                "approach": "示例驱动学习",
                "recommendations": [
                    "优先查看代码示例和案例",
                    "通过对比学习理解概念",
                    "重点关注实践操作步骤"
                ],
                "resource_preference": "案例库和示例代码"
            },
            LearningStyle.THEORY_FIRST: {
                "approach": "理论先导学习",
                "recommendations": [
                    "先理解原理再进行实践",
                    "深入学习底层概念和机制",
                    "注重知识体系的完整性"
                ],
                "resource_preference": "理论文档和技术原理"
            },
            LearningStyle.HANDS_ON: {
                "approach": "实践导向学习",
                "recommendations": [
                    "直接动手操作，在实践中学习",
                    "通过试错快速获得经验",
                    "重视项目实战和实际应用"
                ],
                "resource_preference": "实验环境和项目模板"
            },
            LearningStyle.VISUAL: {
                "approach": "可视化学习",
                "recommendations": [
                    "使用图表和流程图理解概念",
                    "关注界面设计和用户体验",
                    "通过视觉化工具辅助学习"
                ],
                "resource_preference": "视频教程和图形化工具"
            }
        }
        
        return style_strategies.get(style, style_strategies[LearningStyle.EXAMPLES_FIRST])
    
    def _analyze_interest_focus(self, interests: List[str]) -> Dict[str, Any]:
        """分析兴趣点，确定学习重点"""
        
        # 将兴趣映射到课程节点
        interest_node_map = {
            "移动端": ["ui_design", "frontend_dev"],
            "Agent": ["api_calling", "no_code_ai", "backend_dev"],
            "RAG": ["rag_system", "backend_dev"],
            "机器学习": ["model_deployment", "rag_system"],
            "Web开发": ["frontend_dev", "backend_dev", "ui_design"],
            "数据分析": ["api_calling", "rag_system"]
        }
        
        priority_nodes = []
        for interest in interests:
            if interest in interest_node_map:
                priority_nodes.extend(interest_node_map[interest])
        
        # 统计节点优先级
        node_priorities = {}
        for node in priority_nodes:
            node_priorities[node] = node_priorities.get(node, 0) + 1
        
        # 排序获得最高优先级的节点
        sorted_priorities = sorted(
            node_priorities.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "priority_nodes": [node for node, count in sorted_priorities],
            "interest_alignment": dict(sorted_priorities),
            "focus_suggestion": self._generate_focus_suggestion(interests)
        }
    
    def _generate_focus_suggestion(self, interests: List[str]) -> str:
        """基于兴趣生成重点建议"""
        if "Agent" in interests and "RAG" in interests:
            return "建议重点关注AI Agent开发和知识检索技术的结合应用"
        elif "移动端" in interests:
            return "建议在UI设计和前端开发环节投入更多精力"
        elif "机器学习" in interests:
            return "建议深入学习模型部署和RAG系统构建"
        else:
            return "建议均衡发展各项技能，打造全栈开发能力"
    
    def _estimate_course_timeline(
        self, 
        initial_channel: Channel, 
        pace_adjustment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """估算整个课程的学习时间线"""
        
        # 基础时间估算（以周为单位）
        base_timeline = {
            "api_calling": 1,
            "model_deployment": 1.5,
            "no_code_ai": 1,
            "rag_system": 2,
            "ui_design": 1.5,
            "frontend_dev": 2.5,
            "backend_dev": 3
        }
        
        # 根据通道调整时间
        channel_multiplier = self.channel_difficulty_map[initial_channel]
        pace_multiplier = pace_adjustment["timeline_multiplier"]
        
        adjusted_timeline = {}
        total_weeks = 0
        
        for node, weeks in base_timeline.items():
            adjusted_weeks = weeks * channel_multiplier * pace_multiplier
            adjusted_timeline[node] = round(adjusted_weeks, 1)
            total_weeks += adjusted_weeks
        
        return {
            "node_timeline": adjusted_timeline,
            "total_weeks": round(total_weeks, 1),
            "estimated_completion": (datetime.now() + timedelta(weeks=total_weeks)).strftime("%Y-%m-%d"),
            "pace_level": pace_adjustment["pace_level"]
        }
    
    def _get_initial_resources(self, profile: StudentProfile) -> List[Dict[str, Any]]:
        """获取初始推荐资源"""
        resources = []
        
        # 基于学习水平推荐资源
        if profile.level == LearningLevel.L0:
            resources.extend([
                {"type": "基础教程", "title": "Python编程入门", "priority": "高"},
                {"type": "工具指南", "title": "开发环境搭建", "priority": "高"},
                {"type": "概念解释", "title": "API和Web服务基础", "priority": "中"}
            ])
        
        # 基于薄弱技能推荐资源
        for skill in profile.weak_skills[:3]:  # 最多推荐3个技能的资源
            resources.append({
                "type": "补强资源",
                "title": f"{skill}专项练习",
                "priority": "中"
            })
        
        # 基于兴趣推荐资源
        for interest in profile.interests[:2]:  # 最多推荐2个兴趣的资源
            resources.append({
                "type": "兴趣拓展",
                "title": f"{interest}实战案例",
                "priority": "低"
            })
        
        return resources
    
    def _define_monitoring_checkpoints(self) -> List[Dict[str, Any]]:
        """定义学习监控检查点"""
        return [
            {
                "checkpoint": "第1周结束",
                "focus": "API调用基础掌握情况",
                "metrics": ["完成率", "正确率", "学习时间"]
            },
            {
                "checkpoint": "第3周结束", 
                "focus": "模型部署和无代码应用进展",
                "metrics": ["项目质量", "概念理解", "实践能力"]
            },
            {
                "checkpoint": "第6周结束",
                "focus": "RAG系统和UI设计能力",
                "metrics": ["系统复杂度", "设计质量", "用户反馈"]
            },
            {
                "checkpoint": "课程结束",
                "focus": "完整项目交付能力",
                "metrics": ["项目完整度", "技术深度", "创新程度"]
            }
        ]
    
    async def recommend_path_adjustment(
        self,
        student_id: str,
        current_progress: Dict[str, Any],
        recent_assessments: List[Dict[str, Any]],
        behavioral_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        基于学习进展推荐路径调整
        
        Args:
            student_id: 学生ID
            current_progress: 当前学习进度
            recent_assessments: 最近的评估结果
            behavioral_data: 学习行为数据
            
        Returns:
            路径调整建议
        """
        
        # 分析当前表现
        performance_analysis = self._analyze_recent_performance(recent_assessments)
        
        # 分析学习行为模式
        behavior_analysis = self._analyze_learning_behavior(behavioral_data)
        
        # 检测学习困难
        difficulty_indicators = self._detect_learning_difficulties(
            performance_analysis, behavior_analysis
        )
        
        # 生成调整建议
        adjustment_decision = self._make_adjustment_decision(
            current_progress, performance_analysis, difficulty_indicators
        )
        
        # 计算置信度
        confidence_score = self._calculate_recommendation_confidence(
            performance_analysis, behavior_analysis
        )
        
        recommendation = {
            "student_id": student_id,
            "adjustment_type": adjustment_decision["type"],
            "current_analysis": {
                "performance": performance_analysis,
                "behavior_patterns": behavior_analysis,
                "difficulty_signals": difficulty_indicators
            },
            "recommended_actions": adjustment_decision["actions"],
            "confidence_score": confidence_score,
            "reasoning": adjustment_decision["reasoning"],
            "expected_outcomes": adjustment_decision["expected_outcomes"],
            "monitoring_plan": self._create_monitoring_plan(adjustment_decision),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"🤖 路径调整建议已生成: {student_id} -> {adjustment_decision['type']}")
        return recommendation
    
    def _analyze_recent_performance(
        self, 
        recent_assessments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析最近的学习表现"""
        
        if not recent_assessments:
            return {"trend": "insufficient_data", "average_score": 0, "consistency": 0}
        
        scores = [assessment.get("overall_score", 0) for assessment in recent_assessments]
        
        # 计算趋势
        if len(scores) >= 3:
            recent_trend = np.polyfit(range(len(scores)), scores, 1)[0]
            if recent_trend > 5:
                trend = "improving"
            elif recent_trend < -5:
                trend = "declining" 
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # 计算一致性（标准差）
        consistency = float(np.std(scores)) if len(scores) > 1 else 0
        
        # 分析具体维度表现
        dimension_analysis = self._analyze_dimension_performance(recent_assessments)
        
        return {
            "trend": trend,
            "average_score": float(np.mean(scores)),
            "consistency": consistency,
            "score_range": {"min": min(scores), "max": max(scores)},
            "recent_scores": scores[-3:],  # 最近3次得分
            "dimension_breakdown": dimension_analysis
        }
    
    def _analyze_dimension_performance(
        self, 
        assessments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析各维度表现"""
        
        dimensions = ["idea", "ui", "code"]
        analysis = {}
        
        for dim in dimensions:
            dim_scores = []
            for assessment in assessments:
                breakdown = assessment.get("breakdown", {})
                if dim in breakdown:
                    dim_scores.append(breakdown[dim])
            
            if dim_scores:
                analysis[dim] = {
                    "average": float(np.mean(dim_scores)),
                    "trend": "stable",  # 简化处理
                    "lowest_score": min(dim_scores),
                    "needs_attention": float(np.mean(dim_scores)) < 60
                }
        
        return analysis
    
    def _analyze_learning_behavior(
        self, 
        behavioral_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析学习行为模式"""
        
        if not behavioral_data:
            return {"pattern": "unknown", "engagement": "medium", "risk_factors": []}
        
        # 分析学习时间模式
        study_hours = behavioral_data.get("weekly_study_hours", [])
        if study_hours:
            avg_hours = np.mean(study_hours)
            consistency = 1.0 - (np.std(study_hours) / max(avg_hours, 1))
        else:
            avg_hours = 0
            consistency = 0
        
        # 分析提交模式
        submission_pattern = behavioral_data.get("submission_pattern", "regular")
        
        # 分析求助行为
        help_seeking = behavioral_data.get("help_requests", 0)
        
        # 识别风险因素
        risk_factors = []
        if avg_hours < 3:
            risk_factors.append("insufficient_study_time")
        if consistency < 0.5:
            risk_factors.append("irregular_study_pattern")
        if submission_pattern == "last_minute":
            risk_factors.append("procrastination")
        if help_seeking == 0:
            risk_factors.append("isolation")
        
        # 评估参与度
        if avg_hours >= 6 and consistency >= 0.7:
            engagement = "high"
        elif avg_hours >= 3 and consistency >= 0.4:
            engagement = "medium"
        else:
            engagement = "low"
        
        return {
            "pattern": submission_pattern,
            "engagement": engagement,
            "avg_study_hours": avg_hours,
            "consistency": consistency,
            "help_seeking_frequency": help_seeking,
            "risk_factors": risk_factors
        }
    
    def _detect_learning_difficulties(
        self,
        performance_analysis: Dict[str, Any],
        behavior_analysis: Dict[str, Any]
    ) -> List[str]:
        """检测学习困难信号"""
        
        difficulties = []
        
        # 性能相关困难
        if performance_analysis["trend"] == "declining":
            difficulties.append("performance_declining")
        
        if performance_analysis["average_score"] < 50:
            difficulties.append("low_achievement")
        
        if performance_analysis["consistency"] > 20:  # 分数波动过大
            difficulties.append("inconsistent_performance")
        
        # 行为相关困难
        if behavior_analysis["engagement"] == "low":
            difficulties.append("low_engagement")
        
        if "insufficient_study_time" in behavior_analysis["risk_factors"]:
            difficulties.append("time_management")
        
        if "procrastination" in behavior_analysis["risk_factors"]:
            difficulties.append("procrastination")
        
        if "isolation" in behavior_analysis["risk_factors"]:
            difficulties.append("lack_of_support_seeking")
        
        return difficulties
    
    def _make_adjustment_decision(
        self,
        current_progress: Dict[str, Any],
        performance_analysis: Dict[str, Any],
        difficulty_indicators: List[str]
    ) -> Dict[str, Any]:
        """制定调整决策"""
        
        current_channel = current_progress.get("current_channel", "B")
        avg_score = performance_analysis["average_score"]
        
        # 决策逻辑
        if "performance_declining" in difficulty_indicators or "low_achievement" in difficulty_indicators:
            if current_channel == "C":
                decision_type = "downgrade_to_b"
                actions = ["降级到B通道", "提供额外辅导资源", "增加练习时间"]
            elif current_channel == "B":
                decision_type = "downgrade_to_a"
                actions = ["降级到A通道", "专注基础巩固", "安排一对一辅导"]
            else:
                decision_type = "provide_remediation"
                actions = ["提供补救课程", "延长学习时间", "加强基础练习"]
            
            reasoning = "基于最近的学习表现下降，建议降低学习难度，重点巩固基础知识。"
            expected_outcomes = ["提升学习信心", "改善掌握程度", "建立良好学习习惯"]
            
        elif avg_score > 85 and current_channel != "C":
            if current_channel == "A":
                decision_type = "upgrade_to_b"
                actions = ["升级到B通道", "增加实践项目", "挑战更复杂任务"]
            else:
                decision_type = "upgrade_to_c"
                actions = ["升级到C通道", "加入高级项目", "准备竞赛或实习"]
            
            reasoning = "基于优秀的学习表现，建议提升学习挑战度，充分发挥潜能。"
            expected_outcomes = ["提升技能深度", "增强解决复杂问题能力", "为高级应用做准备"]
            
        elif "time_management" in difficulty_indicators:
            decision_type = "adjust_pace"
            actions = ["制定详细学习计划", "设置提醒和检查点", "优化时间分配"]
            
            reasoning = "检测到时间管理问题，建议优化学习节奏和时间安排。"
            expected_outcomes = ["改善学习效率", "提高完成率", "建立良好时间习惯"]
            
        else:
            decision_type = "maintain_current"
            actions = ["保持当前学习路径", "继续稳步推进", "关注薄弱环节"]
            
            reasoning = "当前学习状态良好，建议保持现有路径继续学习。"
            expected_outcomes = ["稳步完成课程", "全面掌握技能", "准备综合应用"]
        
        return {
            "type": decision_type,
            "actions": actions,
            "reasoning": reasoning,
            "expected_outcomes": expected_outcomes
        }
    
    def _calculate_recommendation_confidence(
        self,
        performance_analysis: Dict[str, Any],
        behavior_analysis: Dict[str, Any]
    ) -> float:
        """计算推荐置信度"""
        
        confidence_factors = []
        
        # 数据充分性
        if len(performance_analysis.get("recent_scores", [])) >= 3:
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.1)
        
        # 趋势明确性
        trend = performance_analysis["trend"]
        if trend in ["improving", "declining"]:
            confidence_factors.append(0.3)
        else:
            confidence_factors.append(0.15)
        
        # 一致性
        consistency = performance_analysis["consistency"]
        if consistency < 10:  # 低波动
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.1)
        
        # 行为数据可靠性
        if behavior_analysis["pattern"] != "unknown":
            confidence_factors.append(0.3)
        else:
            confidence_factors.append(0.1)
        
        return min(sum(confidence_factors), 1.0)
    
    def _create_monitoring_plan(self, adjustment_decision: Dict[str, Any]) -> Dict[str, Any]:
        """创建监控计划"""
        
        decision_type = adjustment_decision["type"]
        
        if "downgrade" in decision_type:
            monitoring_frequency = "weekly"
            key_metrics = ["completion_rate", "confidence_level", "error_reduction"]
            intervention_triggers = ["completion_rate < 0.6", "confidence_level < 0.4"]
        elif "upgrade" in decision_type:
            monitoring_frequency = "bi-weekly"
            key_metrics = ["challenge_completion", "innovation_level", "peer_comparison"]
            intervention_triggers = ["challenge_completion < 0.7", "frustration_level > 0.6"]
        else:
            monitoring_frequency = "monthly"
            key_metrics = ["steady_progress", "skill_development", "goal_achievement"]
            intervention_triggers = ["progress_stagnation > 2_weeks"]
        
        return {
            "frequency": monitoring_frequency,
            "key_metrics": key_metrics,
            "intervention_triggers": intervention_triggers,
            "review_points": [
                {"weeks": 2, "focus": "adaptation_success"},
                {"weeks": 4, "focus": "outcome_achievement"},
                {"weeks": 6, "focus": "long_term_impact"}
            ]
        }


class PathRecommendationEngineError(Exception):
    """路径推荐引擎错误"""
    pass
