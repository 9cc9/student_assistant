"""评分聚合器"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from ..models.assessment import (
    ScoreBreakdown, DetailedScores, Diagnosis, ExitRule,
    IdeaScore, UIScore, CodeScore
)
from ..config.settings import assessment_config, get_exit_rules


logger = logging.getLogger(__name__)


class ScoreAggregator:
    """评分聚合器，负责聚合各个评估器的结果"""
    
    def __init__(self):
        self.config = assessment_config
        self.exit_rules = get_exit_rules()
    
    def aggregate_scores(self, evaluation_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合各个评估器的评分结果
        
        Args:
            evaluation_results: 各评估器的结果字典
                - "idea": Idea评估结果
                - "ui": UI评估结果  
                - "code": 代码评估结果
                
        Returns:
            聚合后的评估结果
        """
        try:
            # 提取各维度评分
            idea_result = evaluation_results.get("idea", {})
            ui_result = evaluation_results.get("ui", {})
            code_result = evaluation_results.get("code", {})
            
            idea_score = idea_result.get("overall_score", 0)
            ui_score = ui_result.get("overall_score", 0)
            code_score = code_result.get("overall_score", 0)
            
            # 创建评分细分
            score_breakdown = ScoreBreakdown(
                idea=idea_score,
                ui=ui_score,
                code=code_score
            )
            
            # 创建详细评分（如果有的话）
            detailed_scores = None
            if all([idea_result.get("score"), ui_result.get("score"), code_result.get("score")]):
                detailed_scores = DetailedScores(
                    idea=idea_result["score"],
                    ui=ui_result["score"],
                    code=code_result["score"]
                )
            
            # 聚合诊断信息
            all_diagnoses = []
            for result in [idea_result, ui_result, code_result]:
                all_diagnoses.extend(result.get("diagnoses", []))
            
            # 按优先级排序诊断信息
            all_diagnoses.sort(key=lambda d: d.priority if hasattr(d, 'priority') else 1)
            
            # 聚合学习资源
            all_resources = []
            for result in [idea_result, ui_result, code_result]:
                all_resources.extend(result.get("resources", []))
            
            # 去重并排序资源
            unique_resources = list(set(all_resources))
            
            # 生成准出规则
            exit_rules = self._generate_exit_rules(
                detailed_scores or score_breakdown,
                all_diagnoses
            )
            
            # 生成综合反馈
            comprehensive_feedback = self._generate_comprehensive_feedback(
                score_breakdown, all_diagnoses, evaluation_results
            )
            
            logger.info(f"评分聚合完成，综合分数: {score_breakdown.overall_score}")
            
            return {
                "score_breakdown": score_breakdown,
                "detailed_scores": detailed_scores,
                "overall_score": score_breakdown.overall_score,
                "diagnoses": all_diagnoses,
                "resources": unique_resources,
                "exit_rules": exit_rules,
                "comprehensive_feedback": comprehensive_feedback,
                "evaluation_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"评分聚合失败: {str(e)}")
            raise AggregationError(f"评分聚合失败: {str(e)}")
    
    def _generate_exit_rules(self, scores, diagnoses: List[Diagnosis]) -> ExitRule:
        """
        生成准出规则
        
        Args:
            scores: 评分对象
            diagnoses: 诊断信息列表
            
        Returns:
            准出规则对象
        """
        pass_status = True
        path_update = {}
        remedy = []
        
        # 获取各维度分数
        if isinstance(scores, ScoreBreakdown):
            idea_score = scores.idea
            ui_score = scores.ui  
            code_score = scores.code
        else:  # DetailedScores
            idea_score = scores.idea.overall
            ui_score = scores.ui.overall
            code_score = scores.code.overall
        
        overall_score = scores.overall_score if hasattr(scores, 'overall_score') else \
                       (idea_score * 0.3 + ui_score * 0.3 + code_score * 0.4)
        
        # 检查总体通过情况
        if overall_score < self.config.PASS_THRESHOLD:
            pass_status = False
        
        # 应用具体的准出规则
        for rule_id, rule_config in self.exit_rules.items():
            condition = rule_config["condition"]
            
            # 解析并检查条件
            if self._check_exit_condition(condition, scores):
                pass_status = False
                remedy.append(rule_config["message"])
                
                # 添加阻塞节点
                if "block_nodes" in rule_config:
                    path_update["blocked_nodes"] = rule_config["block_nodes"]
                
                # 添加需要的交付物
                if "deliverables" in rule_config:
                    path_update["required_deliverables"] = rule_config["deliverables"]
        
        # 推荐学习路径调整
        if pass_status:
            if overall_score >= self.config.EXCELLENT_THRESHOLD:
                path_update["recommend_channel"] = "C"  # 升级到挑战通道
                path_update["unlock_nodes"] = self._get_advanced_nodes(scores)
            elif overall_score >= self.config.PASS_THRESHOLD:
                path_update["recommend_channel"] = "B"  # 保持标准通道
            else:
                path_update["recommend_channel"] = "A"  # 降级到基础通道
        else:
            # 不通过时的补救路径
            path_update["recommend_channel"] = "A"
            remedy.extend(self._generate_remedial_actions(diagnoses))
        
        return ExitRule(
            pass_status=pass_status,
            path_update=path_update,
            remedy=remedy
        )
    
    def _check_exit_condition(self, condition: str, scores) -> bool:
        """
        检查准出条件
        
        Args:
            condition: 条件字符串，如"code.correctness < 70"
            scores: 评分对象
            
        Returns:
            条件是否满足
        """
        try:
            # 解析条件
            if "code.correctness" in condition:
                if hasattr(scores, 'code') and hasattr(scores.code, 'correctness'):
                    score_value = scores.code.correctness
                else:
                    return False
            elif "ui.usability" in condition:
                if hasattr(scores, 'ui') and hasattr(scores.ui, 'usability'):
                    score_value = scores.ui.usability
                else:
                    return False
            elif "idea.feasibility" in condition:
                if hasattr(scores, 'idea') and hasattr(scores.idea, 'feasibility'):
                    score_value = scores.idea.feasibility
                else:
                    return False
            else:
                return False
            
            # 解析比较操作
            if " < " in condition:
                threshold = float(condition.split(" < ")[1])
                return score_value < threshold
            elif " > " in condition:
                threshold = float(condition.split(" > ")[1])
                return score_value > threshold
            elif " <= " in condition:
                threshold = float(condition.split(" <= ")[1])
                return score_value <= threshold
            elif " >= " in condition:
                threshold = float(condition.split(" >= ")[1])
                return score_value >= threshold
            
            return False
            
        except Exception as e:
            logger.warning(f"准出条件检查失败: {condition}, 错误: {str(e)}")
            return False
    
    def _get_advanced_nodes(self, scores) -> List[str]:
        """获取可解锁的高级节点"""
        advanced_nodes = []
        
        # 根据优秀的维度推荐相应的高级节点
        if hasattr(scores, 'code') and hasattr(scores.code, 'architecture'):
            if scores.code.architecture >= 85:
                advanced_nodes.extend(["microservices", "distributed-systems"])
        
        if hasattr(scores, 'ui') and hasattr(scores.ui, 'information_arch'):
            if scores.ui.information_arch >= 85:
                advanced_nodes.extend(["advanced-ui-patterns", "ux-optimization"])
        
        if hasattr(scores, 'idea') and hasattr(scores.idea, 'innovation'):
            if scores.idea.innovation >= 85:
                advanced_nodes.extend(["innovation-lab", "research-project"])
        
        return advanced_nodes
    
    def _generate_remedial_actions(self, diagnoses: List[Diagnosis]) -> List[str]:
        """生成补救措施"""
        remedial_actions = []
        
        # 基于诊断信息生成具体的补救措施
        for diagnosis in diagnoses[:5]:  # 取前5个最重要的诊断
            if diagnosis.dimension.startswith("code."):
                remedial_actions.append(f"代码改进：{diagnosis.fix}")
            elif diagnosis.dimension.startswith("ui."):
                remedial_actions.append(f"UI优化：{diagnosis.fix}")
            elif diagnosis.dimension.startswith("idea."):
                remedial_actions.append(f"创意完善：{diagnosis.fix}")
        
        return remedial_actions
    
    def _generate_comprehensive_feedback(self, score_breakdown: ScoreBreakdown,
                                       diagnoses: List[Diagnosis],
                                       evaluation_results: Dict[str, Any]) -> str:
        """
        生成综合反馈
        
        Args:
            score_breakdown: 评分细分
            diagnoses: 诊断信息
            evaluation_results: 原始评估结果
            
        Returns:
            综合反馈文本
        """
        feedback_parts = []
        
        # 总体评价
        overall_score = score_breakdown.overall_score
        if overall_score >= 85:
            feedback_parts.append("🎉 恭喜！您的作品质量优秀，展现了很强的技术能力和创新思维。")
        elif overall_score >= 60:
            feedback_parts.append("✅ 您的作品已达到通过标准，在多个方面表现良好。")
        else:
            feedback_parts.append("⚠️ 您的作品还有改进空间，建议根据以下建议进行优化。")
        
        # 各维度表现
        feedback_parts.append("\n📊 各维度评分：")
        feedback_parts.append(f"• 创意想法：{score_breakdown.idea:.1f}分 ({self._get_score_level(score_breakdown.idea)})")
        feedback_parts.append(f"• UI设计：{score_breakdown.ui:.1f}分 ({self._get_score_level(score_breakdown.ui)})")
        feedback_parts.append(f"• 代码质量：{score_breakdown.code:.1f}分 ({self._get_score_level(score_breakdown.code)})")
        
        # 主要亮点
        highlights = self._extract_highlights(score_breakdown, evaluation_results)
        if highlights:
            feedback_parts.append(f"\n✨ 主要亮点：\n{highlights}")
        
        # 改进建议
        if diagnoses:
            feedback_parts.append("\n🔧 改进建议：")
            for i, diagnosis in enumerate(diagnoses[:3], 1):  # 显示前3个最重要的建议
                feedback_parts.append(f"{i}. {diagnosis.issue}：{diagnosis.fix}")
        
        return "\n".join(feedback_parts)
    
    def _get_score_level(self, score: float) -> str:
        """获取分数等级描述"""
        if score >= 85:
            return "优秀"
        elif score >= 75:
            return "良好"
        elif score >= 60:
            return "及格"
        else:
            return "需改进"
    
    def _extract_highlights(self, score_breakdown: ScoreBreakdown,
                          evaluation_results: Dict[str, Any]) -> str:
        """提取作品亮点"""
        highlights = []
        
        # 找出得分较高的维度
        if score_breakdown.idea >= 80:
            highlights.append("创意富有创新性和可行性")
        
        if score_breakdown.ui >= 80:
            highlights.append("UI设计规范且用户体验良好")
            
        if score_breakdown.code >= 80:
            highlights.append("代码质量较高，结构清晰")
        
        # 从评估结果中提取更具体的亮点
        for category, result in evaluation_results.items():
            feedback = result.get("feedback", "")
            if "优秀" in feedback or "很好" in feedback:
                # 可以进一步解析具体的优点
                pass
        
        return "• " + "\n• ".join(highlights) if highlights else ""


class AggregationError(Exception):
    """聚合错误"""
    pass


