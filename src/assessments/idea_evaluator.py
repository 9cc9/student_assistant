"""Idea评估器"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseEvaluator, EvaluationResult
from ..models import ScoreBreakdown, Diagnosis, ScoreDimension


class IdeaEvaluator(BaseEvaluator):
    """Idea评估器 - 评估创新性、可行性、学习价值"""
    
    WEIGHTS = {
        ScoreDimension.IDEA_INNOVATION: 0.4,      # 创新性 40%
        ScoreDimension.IDEA_FEASIBILITY: 0.4,     # 可行性 40%
        ScoreDimension.IDEA_LEARNING_VALUE: 0.2   # 学习价值 20%
    }
    
    def _get_category(self) -> str:
        return "idea"
    
    async def evaluate(self, content: str, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        """评估Idea"""
        start_time = time.time()
        
        if not self._validate_input(content):
            raise ValueError("Idea内容不能为空")
        
        # 分析文本内容
        analysis = await self._analyze_idea_text(content)
        
        # 生成各维度评分
        breakdown = [
            await self._evaluate_innovation(content, analysis),
            await self._evaluate_feasibility(content, analysis),
            await self._evaluate_learning_value(content, analysis)
        ]
        
        # 计算总分
        overall_score = self._calculate_score(breakdown)
        
        # 生成诊断
        diagnosis = self._generate_diagnosis(breakdown, analysis)
        
        # 收集证据
        evidence = self._collect_evidence(content, analysis)
        
        processing_time = time.time() - start_time
        
        return EvaluationResult(
            category=self.category,
            overall_score=overall_score,
            breakdown=breakdown,
            diagnosis=diagnosis,
            evidence=evidence,
            processing_time=processing_time,
            created_at=datetime.now()
        )
    
    async def _analyze_idea_text(self, content: str) -> Dict[str, Any]:
        """分析Idea文本"""
        # 基础文本分析
        word_count = len(content.split())
        char_count = len(content)
        
        # 关键词分析
        innovation_keywords = ["新颖", "创新", "原创", "独特", "前沿", "突破", "AI", "机器学习", "深度学习"]
        feasibility_keywords = ["实现", "开发", "技术", "框架", "API", "数据库", "架构"]
        learning_keywords = ["学习", "掌握", "练习", "提升", "技能", "知识"]
        
        innovation_count = sum(1 for keyword in innovation_keywords if keyword in content)
        feasibility_count = sum(1 for keyword in feasibility_keywords if keyword in content)
        learning_count = sum(1 for keyword in learning_keywords if keyword in content)
        
        # 技术复杂度分析
        tech_stack_mentions = 0
        complex_concepts = ["分布式", "微服务", "并发", "异步", "缓存", "负载均衡", "容器化"]
        for concept in complex_concepts:
            if concept in content:
                tech_stack_mentions += 1
        
        return {
            "word_count": word_count,
            "char_count": char_count,
            "innovation_indicators": innovation_count,
            "feasibility_indicators": feasibility_count,
            "learning_indicators": learning_count,
            "tech_complexity": tech_stack_mentions,
            "has_clear_problem": "问题" in content or "需求" in content,
            "has_solution": "解决" in content or "方案" in content,
            "has_tech_details": any(tech in content for tech in ["Python", "JavaScript", "React", "Vue", "FastAPI", "Django"])
        }
    
    async def _evaluate_innovation(self, content: str, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估创新性"""
        base_score = 50  # 基础分
        
        # 创新指标加分
        innovation_score = min(analysis["innovation_indicators"] * 5, 30)
        
        # 技术新颖度加分
        tech_novelty_score = min(analysis["tech_complexity"] * 3, 20)
        
        # 问题定义清晰度
        problem_clarity_score = 10 if analysis["has_clear_problem"] else -10
        
        total_score = min(base_score + innovation_score + tech_novelty_score + problem_clarity_score, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if analysis["innovation_indicators"] < 2:
            issues.append("创新性表达不足")
            suggestions.append("突出项目的新颖性和与现有解决方案的差异")
        
        if not analysis["has_clear_problem"]:
            issues.append("问题定义不够清晰")
            suggestions.append("明确说明要解决的具体问题")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.IDEA_INNOVATION,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.IDEA_INNOVATION],
            evidence=[f"创新指标数量: {analysis['innovation_indicators']}", f"技术复杂度: {analysis['tech_complexity']}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_feasibility(self, content: str, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估可行性"""
        base_score = 60  # 基础分
        
        # 技术可行性
        tech_feasibility_score = min(analysis["feasibility_indicators"] * 4, 25)
        
        # 技术细节完整性
        tech_details_score = 15 if analysis["has_tech_details"] else -15
        
        # 解决方案清晰度
        solution_score = 10 if analysis["has_solution"] else -10
        
        # 复杂度合理性(过于复杂会降分)
        complexity_penalty = max((analysis["tech_complexity"] - 5) * 5, 0) if analysis["tech_complexity"] > 5 else 0
        
        total_score = min(base_score + tech_feasibility_score + tech_details_score + solution_score - complexity_penalty, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if not analysis["has_tech_details"]:
            issues.append("技术实现细节不足")
            suggestions.append("补充具体的技术栈和实现方案")
        
        if analysis["tech_complexity"] > 7:
            issues.append("技术复杂度过高，可能难以在课程周期内完成")
            suggestions.append("简化技术方案，聚焦核心功能")
        
        if analysis["word_count"] < 200:
            issues.append("描述过于简单")
            suggestions.append("详细说明实现步骤和技术选型")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.IDEA_FEASIBILITY,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.IDEA_FEASIBILITY],
            evidence=[f"技术指标数量: {analysis['feasibility_indicators']}", f"字数: {analysis['word_count']}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_learning_value(self, content: str, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估学习价值"""
        base_score = 60
        
        # 学习指标
        learning_score = min(analysis["learning_indicators"] * 6, 25)
        
        # 技能覆盖度
        skill_coverage_score = min(analysis["tech_complexity"] * 2, 15)
        
        total_score = min(base_score + learning_score + skill_coverage_score, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if analysis["learning_indicators"] < 1:
            issues.append("学习目标不明确")
            suggestions.append("明确说明通过此项目能学习到的技能和知识点")
        
        if analysis["tech_complexity"] < 2:
            issues.append("技术挑战性不足")
            suggestions.append("增加技术深度，涉及更多技能点")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.IDEA_LEARNING_VALUE,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.IDEA_LEARNING_VALUE],
            evidence=[f"学习指标: {analysis['learning_indicators']}", f"技能覆盖度: {analysis['tech_complexity']}"],
            issues=issues,
            suggestions=suggestions
        )
    
    def _calculate_score(self, breakdown: List[ScoreBreakdown]) -> float:
        """计算加权总分"""
        total_score = 0
        for item in breakdown:
            total_score += item.score * item.weight
        return round(total_score, 1)
    
    def _generate_diagnosis(self, breakdown: List[ScoreBreakdown], analysis: Dict[str, Any]) -> List[Diagnosis]:
        """生成诊断结果"""
        diagnosis = []
        
        for item in breakdown:
            for issue in item.issues:
                severity = "major"
                if item.score < 50:
                    severity = "critical"
                elif item.score > 75:
                    severity = "minor"
                
                # 找到对应的建议
                suggestion_idx = item.issues.index(issue)
                fix = item.suggestions[suggestion_idx] if suggestion_idx < len(item.suggestions) else "需要改进"
                
                diagnosis.append(Diagnosis(
                    dimension=item.dimension,
                    issue=issue,
                    fix=fix,
                    priority=1 if severity == "critical" else 2 if severity == "major" else 3
                ))
        
        return diagnosis
    
    def _collect_evidence(self, content: str, analysis: Dict[str, Any]) -> List[str]:
        """收集评估证据"""
        evidence = [
            f"文本长度: {analysis['word_count']} 词",
            f"创新指标: {analysis['innovation_indicators']} 个",
            f"可行性指标: {analysis['feasibility_indicators']} 个",
            f"学习指标: {analysis['learning_indicators']} 个",
            f"技术复杂度: {analysis['tech_complexity']}"
        ]
        
        if analysis["has_clear_problem"]:
            evidence.append("✓ 包含问题定义")
        if analysis["has_solution"]:
            evidence.append("✓ 包含解决方案")
        if analysis["has_tech_details"]:
            evidence.append("✓ 包含技术细节")
        
        return evidence

