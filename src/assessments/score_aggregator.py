"""评分聚合器"""

from typing import List, Dict, Any
from datetime import datetime

from .base import EvaluationResult
from ..models import AssessmentResult, Diagnosis, ExitRule, ScoreBreakdown


class ScoreAggregator:
    """评分聚合器 - 将Idea、UI、Code三个维度的评估结果聚合为最终评估结果"""
    
    # 三个维度的权重
    CATEGORY_WEIGHTS = {
        "idea": 0.30,  # Idea权重30%
        "ui": 0.30,    # UI权重30%
        "code": 0.40   # Code权重40%
    }
    
    # 通过标准
    PASS_THRESHOLD = 60.0
    EXCELLENT_THRESHOLD = 85.0
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def aggregate_scores(
        self,
        evaluation_results: List[EvaluationResult],
        assessment_id: str,
        student_id: str
    ) -> AssessmentResult:
        """
        聚合多个评估结果
        
        Args:
            evaluation_results: 各维度评估结果列表
            assessment_id: 评估ID
            student_id: 学生ID
            
        Returns:
            AssessmentResult: 聚合后的评估结果
        """
        # 验证输入
        if not evaluation_results:
            raise ValueError("评估结果列表不能为空")
        
        # 按类别组织评估结果
        results_by_category = {result.category: result for result in evaluation_results}
        
        # 计算各类别得分
        category_scores = {}
        for category, weight in self.CATEGORY_WEIGHTS.items():
            if category in results_by_category:
                category_scores[category] = results_by_category[category].overall_score
            else:
                # 如果某个维度缺失，给予较低的默认分数
                category_scores[category] = 50.0
        
        # 计算加权总分
        overall_score = sum(
            category_scores[category] * weight 
            for category, weight in self.CATEGORY_WEIGHTS.items()
        )
        
        # 合并详细分解
        breakdown = []
        for result in evaluation_results:
            breakdown.extend(result.breakdown)
        
        # 合并诊断结果
        diagnosis = self._merge_diagnosis(evaluation_results)
        
        # 生成学习资源推荐
        resources = self._generate_resource_recommendations(diagnosis, category_scores)
        
        # 生成准出规则
        exit_rules = self._generate_exit_rules(category_scores, diagnosis)
        
        # 生成总体反馈
        feedback = self._generate_feedback(overall_score, category_scores, diagnosis)
        
        # 收集证据链接
        evidence_links = self._collect_evidence_links(evaluation_results)
        
        return AssessmentResult(
            assessment_id=assessment_id,
            student_id=student_id,
            overall_score=round(overall_score, 1),
            category_scores=category_scores,
            breakdown=breakdown,
            diagnosis=diagnosis,
            resources=resources,
            exit_rules=exit_rules,
            feedback=feedback,
            evidence_links=evidence_links,
            created_at=datetime.now()
        )
    
    def _merge_diagnosis(self, evaluation_results: List[EvaluationResult]) -> List[Diagnosis]:
        """合并诊断结果，去重并按严重程度排序"""
        all_diagnosis = []
        
        for result in evaluation_results:
            all_diagnosis.extend(result.diagnosis)
        
        # 按优先级排序 (Diagnosis类使用priority字段，1最高)
        all_diagnosis.sort(key=lambda x: x.priority)
        
        # 去重(基于dimension和issue)
        seen = set()
        unique_diagnosis = []
        for item in all_diagnosis:
            key = (item.dimension, item.issue)
            if key not in seen:
                seen.add(key)
                unique_diagnosis.append(item)
        
        return unique_diagnosis
    
    def _generate_resource_recommendations(
        self, 
        diagnosis: List[Diagnosis], 
        category_scores: Dict[str, float]
    ) -> List[str]:
        """根据诊断结果生成学习资源推荐"""
        resources = []
        
        # 基于分数推荐资源
        if category_scores.get("idea", 0) < 70:
            resources.extend([
                "创新思维训练教程",
                "项目需求分析指南",
                "技术可行性评估方法"
            ])
        
        if category_scores.get("ui", 0) < 70:
            resources.extend([
                "UI设计规范指南",
                "可访问性设计教程",
                "色彩对比度工具使用说明",
                "移动端设计最佳实践"
            ])
        
        if category_scores.get("code", 0) < 70:
            resources.extend([
                "Python编码规范(PEP8)",
                "单元测试编写指南",
                "代码重构技巧",
                "安全编码实践"
            ])
        
        # 基于特定问题推荐资源
        for item in diagnosis[:5]:  # 只处理前5个最严重的问题
            if "对比度" in item.issue:
                resources.append("WCAG颜色对比度标准")
            elif "测试" in item.issue:
                resources.append("pytest使用教程")
            elif "复杂度" in item.issue:
                resources.append("代码复杂度管理")
            elif "安全" in item.issue:
                resources.append("Python安全编程指南")
        
        # 去重并限制数量
        return list(dict.fromkeys(resources))[:10]
    
    def _generate_exit_rules(
        self, 
        category_scores: Dict[str, float], 
        diagnosis: List[Diagnosis]
    ) -> ExitRule:
        """生成准出规则"""
        # 判断是否通过
        overall_score = sum(
            category_scores[cat] * weight 
            for cat, weight in self.CATEGORY_WEIGHTS.items()
        )
        
        pass_status = overall_score >= self.PASS_THRESHOLD
        
        # 路径更新信息
        path_update = {}
        if pass_status:
            if overall_score >= self.EXCELLENT_THRESHOLD:
                path_update["recommend_channel"] = "C"  # 挑战通道
                path_update["unlock_nodes"] = ["高级项目", "竞赛准备"]
            else:
                path_update["recommend_channel"] = "B"  # 标准通道
                path_update["unlock_nodes"] = ["下一阶段项目"]
        else:
            path_update["recommend_channel"] = "A"  # 基础通道
            path_update["require_remediation"] = True
        
        # 补救措施
        remedy = []
        requirements = []
        
        # 基于具体问题生成补救措施
        critical_issues = [d for d in diagnosis if d.priority == 1]
        
        for issue in critical_issues:
            if "code.correctness" in issue.dimension and category_scores.get("code", 0) < 70:
                remedy.append("必须修复语法错误并通过代码审查")
                requirements.append("代码能够正常运行")
            
            if "code.robustness" in issue.dimension:
                remedy.append("补充单元测试，覆盖率达到80%以上")
                requirements.append("单元测试覆盖率≥80%")
            
            if "ui.accessibility" in issue.dimension and category_scores.get("ui", 0) < 60:
                remedy.append("修复对比度问题，确保可访问性")
                requirements.append("颜色对比度≥4.5:1，触控目标≥44pt")
            
            if "idea.feasibility" in issue.dimension and category_scores.get("idea", 0) < 65:
                remedy.append("补充技术可行性分析文档")
                requirements.append("提交详细的技术实现方案")
        
        # 如果没有严重问题但分数不够，给出通用建议
        if not remedy and not pass_status:
            if category_scores.get("code", 0) < self.PASS_THRESHOLD:
                remedy.append("完善代码实现，提高代码质量")
            if category_scores.get("ui", 0) < self.PASS_THRESHOLD:
                remedy.append("改进界面设计，提升用户体验")
            if category_scores.get("idea", 0) < self.PASS_THRESHOLD:
                remedy.append("深化项目理念，增强创新性")
        
        return ExitRule(
            pass_status=pass_status,
            path_update=path_update,
            remedy=remedy,
            requirements=requirements
        )
    
    def _generate_feedback(
        self,
        overall_score: float,
        category_scores: Dict[str, float],
        diagnosis: List[Diagnosis]
    ) -> str:
        """生成总体反馈"""
        feedback_parts = []
        
        # 总体评价
        if overall_score >= self.EXCELLENT_THRESHOLD:
            feedback_parts.append(f"优秀！总分{overall_score:.1f}分，项目质量很高。")
        elif overall_score >= self.PASS_THRESHOLD:
            feedback_parts.append(f"良好，总分{overall_score:.1f}分，项目达到了基本要求。")
        else:
            feedback_parts.append(f"需要改进，总分{overall_score:.1f}分，距离通过标准还有差距。")
        
        # 各维度分析
        feedback_parts.append("\n各维度表现：")
        
        for category, score in category_scores.items():
            category_name = {"idea": "创意设计", "ui": "界面设计", "code": "代码实现"}[category]
            if score >= 80:
                feedback_parts.append(f"• {category_name}: {score:.1f}分 - 表现出色")
            elif score >= 60:
                feedback_parts.append(f"• {category_name}: {score:.1f}分 - 达到要求")
            else:
                feedback_parts.append(f"• {category_name}: {score:.1f}分 - 需要改进")
        
        # 主要问题
        critical_issues = [d for d in diagnosis if d.priority == 1]
        if critical_issues:
            feedback_parts.append(f"\n需要重点关注的问题：")
            for issue in critical_issues[:3]:  # 只显示前3个
                feedback_parts.append(f"• {issue.issue}")
        
        # 改进建议
        if overall_score < self.PASS_THRESHOLD:
            feedback_parts.append("\n建议优先解决上述关键问题，然后重新提交评估。")
        elif overall_score < self.EXCELLENT_THRESHOLD:
            feedback_parts.append("\n项目已达到基本要求，可以继续完善细节，追求更高品质。")
        else:
            feedback_parts.append("\n项目质量优秀，可以考虑挑战更高难度的任务。")
        
        return "".join(feedback_parts)
    
    def _collect_evidence_links(self, evaluation_results: List[EvaluationResult]) -> List[str]:
        """收集证据链接"""
        evidence_links = []
        
        for result in evaluation_results:
            category_link = f"evaluation_evidence_{result.category}_{result.created_at.isoformat()}"
            evidence_links.append(category_link)
            
            # 如果有具体的证据，也加入链接
            for evidence in result.evidence:
                if evidence.startswith(('http://', 'https://', 'file://')):
                    evidence_links.append(evidence)
        
        return evidence_links
    
    def get_comparison_analysis(
        self,
        previous_result: AssessmentResult,
        current_result: AssessmentResult
    ) -> Dict[str, Any]:
        """比较两次评估结果"""
        comparison = {
            "overall_improvement": current_result.overall_score - previous_result.overall_score,
            "category_changes": {},
            "resolved_issues": [],
            "new_issues": [],
            "improvement_suggestions": []
        }
        
        # 各类别分数变化
        for category in self.CATEGORY_WEIGHTS.keys():
            prev_score = previous_result.category_scores.get(category, 0)
            curr_score = current_result.category_scores.get(category, 0)
            comparison["category_changes"][category] = curr_score - prev_score
        
        # 问题解决情况
        prev_issues = {(d.dimension, d.issue) for d in previous_result.diagnosis}
        curr_issues = {(d.dimension, d.issue) for d in current_result.diagnosis}
        
        comparison["resolved_issues"] = list(prev_issues - curr_issues)
        comparison["new_issues"] = list(curr_issues - prev_issues)
        
        # 改进建议
        if comparison["overall_improvement"] > 0:
            comparison["improvement_suggestions"].append("继续保持改进势头")
        else:
            comparison["improvement_suggestions"].append("需要重新审视改进方向")
        
        return comparison

