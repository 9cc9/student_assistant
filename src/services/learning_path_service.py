"""学习路径推荐服务核心实现"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import json
from pathlib import Path

from ..models.learning_path import (
    LearningPath, PathNode, Channel, NodeStatus, PathDecision,
    StudentPathProgress, PathRecommendation, CheckpointRule
)
from ..models.student import StudentProfile, LearningLevel, LearningStyle
from .progress_repository import ProgressRepository

logger = logging.getLogger(__name__)


class LearningPathService:
    """学习路径推荐服务类，负责管理个性化学习路径"""
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            
        # 加载学习路径配置（从JSON文件）
        if not hasattr(self, 'learning_paths'):
            self.learning_paths = {}
            self._load_learning_paths_from_config()
            logger.info(f"📚 LearningPathService 已初始化")
    
    def _load_learning_paths_from_config(self):
        """从配置文件加载学习路径"""
        try:
            config_file = Path("config/learning_paths.json")
            if not config_file.exists():
                raise FileNotFoundError("学习路径配置文件不存在: config/learning_paths.json")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for path_id, path_config in config_data.items():
                learning_path = self._create_learning_path_from_config(path_config)
                if learning_path:
                    self.learning_paths[path_id] = learning_path
                    logger.info(f"📚 学习路径已加载: {path_id}, 包含 {len(learning_path.nodes)} 个节点")
            
            if not self.learning_paths:
                raise ValueError("学习路径配置已读取，但未加载到任何学习路径")
            
            logger.info(f"📚 共加载了 {len(self.learning_paths)} 个学习路径")
            
        except Exception as e:
            logger.error(f"📚 加载学习路径配置失败: {str(e)}")
            raise
    
    def _create_learning_path_from_config(self, config: Dict[str, Any]) -> Optional[LearningPath]:
        """从配置数据创建学习路径对象"""
        try:
            # 创建节点列表
            nodes = []
            for node_config in config.get("nodes", []):
                node = self._create_node_from_config(node_config)
                if node:
                    nodes.append(node)
            
            # 创建学习路径
            learning_path = LearningPath(
                id=config["id"],
                name=config["name"],
                description=config["description"],
                nodes=nodes,
                target_audience=config.get("target_audience", []),
                prerequisites_knowledge=config.get("prerequisites_knowledge", []),
                learning_outcomes=config.get("learning_outcomes", [])
            )
            
            return learning_path
            
        except Exception as e:
            logger.error(f"📚 从配置创建学习路径失败: {str(e)}")
            return None
    
    def _create_node_from_config(self, node_config: Dict[str, Any]) -> Optional[PathNode]:
        """从配置数据创建学习节点"""
        try:
            # 解析通道任务
            channel_tasks = {}
            for channel_name, task_config in node_config.get("channel_tasks", {}).items():
                channel = Channel[channel_name]
                channel_tasks[channel] = task_config
            
            # 解析预估时长
            estimated_hours = {}
            for channel_name, hours in node_config.get("estimated_hours", {}).items():
                channel = Channel[channel_name]
                estimated_hours[channel] = hours
            
            # 解析难度等级
            difficulty_level = {}
            for channel_name, level in node_config.get("difficulty_level", {}).items():
                channel = Channel[channel_name]
                difficulty_level[channel] = level
            
            # 创建门槛卡
            checkpoint_config = node_config.get("checkpoint", {})
            checkpoint = CheckpointRule(
                checkpoint_id=checkpoint_config.get("checkpoint_id", f"{node_config['id']}_checkpoint"),
                must_pass=checkpoint_config.get("must_pass", []),
                evidence=checkpoint_config.get("evidence", []),
                auto_grade=checkpoint_config.get("auto_grade", {})
            )
            
            # 创建节点
            node = PathNode(
                id=node_config["id"],
                name=node_config["name"],
                description=node_config["description"],
                order=node_config["order"],
                channel_tasks=channel_tasks,
                prerequisites=node_config.get("prerequisites", []),
                checkpoint=checkpoint,
                remedy_resources=node_config.get("remedy_resources", {}),
                estimated_hours=estimated_hours,
                difficulty_level=difficulty_level
            )
            
            return node
            
        except Exception as e:
            logger.error(f"📚 从配置创建学习节点失败: {str(e)}")
            return None
    
    # 备用节点构造函数已移除，必须依赖配置文件提供所有节点定义
    
    def _get_channel_tasks_for_node(self, node_id: str) -> Dict[Channel, Dict[str, Any]]:
        """获取节点的A/B/C通道任务定义"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.channel_tasks
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的通道任务定义: {node_id}")
    
    def _get_estimated_hours_for_node(self, node_id: str) -> Dict[Channel, int]:
        """获取节点的预估学习时长"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.estimated_hours
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的预估时长: {node_id}")
    
    def _get_difficulty_level_for_node(self, node_id: str) -> Dict[Channel, int]:
        """获取节点的难度等级 (1-10)"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.difficulty_level
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的难度等级: {node_id}")
    
    def _get_checkpoint_requirements(self, node_id: str) -> List[str]:
        """获取门槛卡要求"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.checkpoint.must_pass
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的门槛卡要求: {node_id}")
    
    def _get_checkpoint_evidence(self, node_id: str) -> List[str]:
        """获取门槛卡证据要求"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.checkpoint.evidence
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的门槛卡证据: {node_id}")
    
    def _get_auto_grade_rules(self, node_id: str) -> Dict[str, Any]:
        """获取自动评分规则"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.checkpoint.auto_grade
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的自动评分规则: {node_id}")
    
    def _get_remedy_resources(self, node_id: str) -> Dict[str, List[str]]:
        """获取补救资源"""
        # 从已加载的学习路径中查找节点
        for path in self.learning_paths.values():
            for node in path.nodes:
                if node.id == node_id:
                    return node.remedy_resources
        
        # 未在配置中找到节点
        raise ValueError(f"未找到节点的补救资源: {node_id}")
    
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
        
        # 🔍 检查是否已有学习进度
        existing_progress = ProgressRepository.get_student_progress(student_id)
        if existing_progress:
            logger.warning(f"📚 ⚠️ 学生 {student_id} 已有学习进度，跳过初始化")
            raise LearningPathServiceError(f"学生 {student_id} 已有学习进度，无法重新初始化。如需重新开始学习，请先清除现有进度。")
        
        # 根据学生水平确定起始通道
        initial_channel = self._determine_initial_channel(profile.level)
        
        # 从配置中获取第一个节点（按 order 排序）
        if not self.learning_paths:
            raise ValueError("未加载任何学习路径，无法初始化学生学习路径")
        # 取第一个学习路径
        first_path = next(iter(self.learning_paths.values()))
        if not first_path.nodes:
            raise ValueError("学习路径无任何节点，无法初始化学生学习路径")
        first_node = sorted(first_path.nodes, key=lambda n: n.order)[0]
        first_node_id = first_node.id
        
        # 创建进度跟踪
        progress = StudentPathProgress(
            student_id=student_id,
            current_node_id=first_node_id,  # 从配置的第一个节点开始
            current_channel=initial_channel,
            node_statuses={first_node_id: NodeStatus.AVAILABLE},
            completed_nodes=[],
            mastery_scores={},
            frustration_level=0.0,
            retry_counts={},
            started_at=datetime.now()
        )
        
        # 根据薄弱技能初始化掌握度分数
        for skill in profile.weak_skills:
            progress.mastery_scores[skill] = 0.3  # 薄弱技能起始分数较低
        
        # 持久化到数据库
        ProgressRepository.upsert_student_progress(
            student_id=student_id,
            current_node_id=first_node_id,
            current_channel=initial_channel,
            total_study_hours=0.0,
            frustration_level=0.0,
            started_at=progress.started_at,
            last_activity_at=progress.last_activity_at,
        )
        # 初始化第一个节点状态
        ProgressRepository.upsert_node_progress(
            student_id=student_id,
            node_id=first_node_id,
            status=NodeStatus.AVAILABLE,
            used_channel=None,
            score=None,
            attempt_count=0,
            started_at=None,
            completed_at=None,
        )
        
        logger.info(f"📚 学生学习路径已初始化: {student_id}, 起始通道: {initial_channel.value}")
        return progress
    
    async def clear_student_progress(self, student_id: str) -> bool:
        """清除学生学习进度（用于重新开始学习）"""
        try:
            # 检查是否存在学习进度
            existing_progress = ProgressRepository.get_student_progress(student_id)
            if not existing_progress:
                logger.warning(f"📚 ⚠️ 学生 {student_id} 没有学习进度，无需清除")
                return False
            
            # 清除学生进度数据
            ProgressRepository.clear_student_progress(student_id)
            logger.info(f"📚 ✅ 学生 {student_id} 的学习进度已清除")
            return True
            
        except Exception as e:
            logger.error(f"📚 ❌ 清除学习进度失败: {str(e)}")
            raise LearningPathServiceError(f"清除学习进度失败: {str(e)}")
    
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
        
        db_data = ProgressRepository.get_student_progress(student_id)
        if not db_data:
            raise ValueError(f"学生学习进度不存在: {student_id}")
        p = db_data["progress"]
        progress = StudentPathProgress(
            student_id=student_id,
            current_node_id=p["current_node_id"],
            current_channel=Channel(p["current_channel"]),
            node_statuses={},  # 如有需要可从 nodes 填充
            completed_nodes=[n["node_id"] for n in db_data["nodes"] if n["status"] == NodeStatus.COMPLETED.value],
            completed_channels={
                n["node_id"]: (n["used_channel"] or "") for n in db_data["nodes"] if n["status"] == NodeStatus.COMPLETED.value
            },
            total_study_hours=float(p["total_study_hours"]),
            mastery_scores={},
            frustration_level=float(p["frustration_level"]),
            retry_counts={},
            started_at=p["started_at"],
            last_activity_at=p["last_activity_at"],
            updated_at=p["updated_at"],
        )
        
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
        # 从配置中获取节点序列
        node_sequence = []
        for path in self.learning_paths.values():
            for node in sorted(path.nodes, key=lambda x: x.order):
                node_sequence.append(node.id)
            break  # 只取第一个路径的节点序列
        
        if not node_sequence:
            # 配置异常：没有任何节点
            raise ValueError("学习路径未包含任何节点，无法计算下一个节点")
        
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
            return node_sequence[0] if node_sequence else current_node_id
    
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
        
        db_data = ProgressRepository.get_student_progress(student_id)
        if not db_data:
            raise ValueError(f"学生学习进度不存在: {student_id}")
        p = db_data["progress"]
        progress = StudentPathProgress(
            student_id=student_id,
            current_node_id=p["current_node_id"],
            current_channel=Channel(p["current_channel"]),
            node_statuses={},
            completed_nodes=[n["node_id"] for n in db_data["nodes"] if n["status"] == NodeStatus.COMPLETED.value],
            completed_channels={
                n["node_id"]: (n["used_channel"] or "") for n in db_data["nodes"] if n["status"] == NodeStatus.COMPLETED.value
            },
            total_study_hours=float(p["total_study_hours"]),
            mastery_scores={},
            frustration_level=float(p["frustration_level"]),
            retry_counts={},
            started_at=p["started_at"],
            last_activity_at=p["last_activity_at"],
            updated_at=p["updated_at"],
        )
        
        # 更新节点状态
        progress.node_statuses[node_id] = status
        progress.last_activity_at = datetime.now()
        progress.updated_at = datetime.now()
        
        # 如果节点完成，更新完成列表
        if status == NodeStatus.COMPLETED:
            if node_id not in progress.completed_nodes:
                progress.completed_nodes.append(node_id)
                
                # 记录完成时使用的通道
                progress.completed_channels[node_id] = progress.current_channel.value
                
                # 计算并累加该节点的学习时长
                estimated_hours = self._get_estimated_hours_for_node(node_id)
                node_hours = estimated_hours.get(progress.current_channel, 0)
                progress.total_study_hours += node_hours
                
                logger.info(f"📚 节点完成，累计学习时长: {node_id} -> +{node_hours}小时，总计: {progress.total_study_hours}小时")
            
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
        
        # 持久化到数据库
        ProgressRepository.upsert_student_progress(
            student_id=student_id,
            current_node_id=progress.current_node_id,
            current_channel=progress.current_channel,
            total_study_hours=progress.total_study_hours,
            frustration_level=progress.frustration_level,
            started_at=progress.started_at,
            last_activity_at=progress.last_activity_at,
        )
        ProgressRepository.upsert_node_progress(
            student_id=student_id,
            node_id=node_id,
            status=status,
            used_channel=progress.current_channel if status == NodeStatus.COMPLETED else None,
            score=(assessment_result.get("overall_score") if assessment_result else None),
            attempt_count=progress.retry_counts.get(node_id, 0),
            started_at=None,
            completed_at=(datetime.now() if status == NodeStatus.COMPLETED else None),
        )
        
        logger.info(f"📚 学生进度已更新: {student_id}, 节点: {node_id}, 状态: {status.value}")
    
    def _recalculate_total_study_hours(self, progress: StudentPathProgress) -> None:
        """重新计算累计学习时长"""
        total_hours = 0.0
        
        for node_id in progress.completed_nodes:
            # 获取该节点的预估时长
            estimated_hours = self._get_estimated_hours_for_node(node_id)
            
            # 使用当前通道计算时长（如果历史记录中没有通道信息，默认使用B通道）
            if hasattr(progress, 'node_channels') and progress.node_channels.get(node_id):
                channel = progress.node_channels[node_id]
            else:
                # 如果没有历史通道记录，根据节点完成时间推测使用B通道
                channel = Channel.B
            
            node_hours = estimated_hours.get(channel, estimated_hours.get(Channel.B, 0))
            total_hours += node_hours
            
            logger.debug(f"📚 重新计算: {node_id} ({channel.value}通道) -> {node_hours}小时")
        
        progress.total_study_hours = total_hours
        logger.info(f"📚 重新计算累计学习时长: {total_hours}小时")
    
    def get_student_progress(self, student_id: str) -> Optional[StudentPathProgress]:
        """获取学生学习进度（从数据库）"""
        db_data = ProgressRepository.get_student_progress(student_id)
        if not db_data:
            return None
        p = db_data["progress"]
        progress = StudentPathProgress(
            student_id=student_id,
            current_node_id=p["current_node_id"],
            current_channel=Channel(p["current_channel"]),
            node_statuses={},
            completed_nodes=[n["node_id"] for n in db_data["nodes"] if n["status"] == NodeStatus.COMPLETED.value],
            completed_channels={
                n["node_id"]: (n["used_channel"] or "") for n in db_data["nodes"] if n["status"] == NodeStatus.COMPLETED.value
            },
            total_study_hours=float(p["total_study_hours"]),
            mastery_scores={},
            frustration_level=float(p["frustration_level"]),
            retry_counts={},
            started_at=p["started_at"],
            last_activity_at=p["last_activity_at"],
            updated_at=p["updated_at"],
        )
        if progress.completed_nodes:
            self._recalculate_total_study_hours(progress)
        return progress
    
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
    
    def _load_student_progresses(self):
        """兼容函数（不再使用文件加载）"""
        logger.info("📚 学习进度改为数据库存储，不再从文件加载")
    
    def _save_student_progresses(self):
        """兼容函数（不再使用文件保存）"""
        logger.info("📚 学习进度改为数据库存储，不再写入文件")
    
    def _serialize_progress(self, progress: StudentPathProgress) -> Dict[str, Any]:
        """序列化学习进度对象"""
        try:
            data = {
                "student_id": progress.student_id,
                "current_node_id": progress.current_node_id,
                "current_channel": progress.current_channel.value,
                "node_statuses": {k: v.value for k, v in progress.node_statuses.items()},
                "completed_nodes": progress.completed_nodes,
                "completed_channels": progress.completed_channels,
                "mastery_scores": progress.mastery_scores,
                "frustration_level": progress.frustration_level,
                "retry_counts": progress.retry_counts,
                "total_study_hours": progress.total_study_hours,
                "started_at": progress.started_at.isoformat(),
                "last_activity_at": progress.last_activity_at.isoformat(),
                "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
            }
            return data
        except Exception as e:
            logger.error(f"📚 序列化学习进度失败: {str(e)}")
            return {}
    
    def _deserialize_progress(self, data: Dict[str, Any]) -> Optional[StudentPathProgress]:
        """反序列化学习进度对象"""
        try:
            # 转换枚举值
            current_channel = Channel(data["current_channel"])
            node_statuses = {k: NodeStatus(v) for k, v in data["node_statuses"].items()}
            
            # 转换时间字段
            started_at = datetime.fromisoformat(data["started_at"])
            last_activity_at = datetime.fromisoformat(data["last_activity_at"])
            updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
            
            progress = StudentPathProgress(
                student_id=data["student_id"],
                current_node_id=data["current_node_id"],
                current_channel=current_channel,
                node_statuses=node_statuses,
                completed_nodes=data["completed_nodes"],
                completed_channels=data.get("completed_channels", {}),
                mastery_scores=data["mastery_scores"],
                frustration_level=data["frustration_level"],
                retry_counts=data["retry_counts"],
                total_study_hours=data["total_study_hours"],
                started_at=started_at,
                last_activity_at=last_activity_at,
                updated_at=updated_at
            )
            return progress
        except Exception as e:
            logger.error(f"📚 反序列化学习进度失败: {str(e)}")
            return None


class LearningPathServiceError(Exception):
    """学习路径服务错误"""
    pass
