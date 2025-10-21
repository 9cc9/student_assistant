"""入学诊断服务 - 生成学生画像的核心服务"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os

from ..models.student import StudentProfile, LearningLevel, LearningStyle
from .ai_scoring_service import get_ai_scoring_service

logger = logging.getLogger(__name__)


class DiagnosticService:
    """
    入学诊断服务
    
    通过10-15分钟的基线测评，包括：
    1. 概念小测 - 评估基础概念理解
    2. 代码小题 - 评估编程能力
    3. 工具熟悉度问卷 - 评估技能熟悉程度
    4. 学习偏好调查 - 了解学习风格和时间安排
    
    生成个性化学生画像用于后续路径推荐。
    """
    
    def __init__(self):
        self.diagnostic_data = self._load_diagnostic_questions()
        self.ai_scoring = get_ai_scoring_service()  # 初始化AI评分服务
        logger.info(f"🧪 诊断服务初始化完成，AI评分: {'已启用' if self.ai_scoring.is_enabled() else '未启用'}")
    
    def _load_diagnostic_questions(self) -> Dict[str, Any]:
        """从JSON文件加载诊断题目"""
        try:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            json_path = os.path.join(project_root, 'config', 'diagnostic_questions.json')
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"✅ 成功从JSON文件加载诊断题目: {json_path}")
                return data
        except FileNotFoundError:
            logger.error(f"❌ 诊断题目JSON文件不存在: {json_path}")
            raise DiagnosticServiceError("诊断题目文件不存在")
        except json.JSONDecodeError as e:
            logger.error(f"❌ 诊断题目JSON文件格式错误: {e}")
            raise DiagnosticServiceError("诊断题目文件格式错误")
        except Exception as e:
            logger.error(f"❌ 加载诊断题目失败: {e}")
            raise DiagnosticServiceError(f"加载诊断题目失败: {e}")
    
    
    def get_diagnostic_test(self) -> Dict[str, Any]:
        """
        获取完整的入学诊断测试
        
        返回包含所有测试题目和调查问卷的结构化数据
        """
        return self.diagnostic_data
    
    def evaluate_diagnostic_results(self, student_responses: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估诊断测试结果，生成学生画像数据
        
        Args:
            student_responses: 学生的回答数据
            
        Returns:
            包含各维度得分和画像信息的结果
        """
        try:
            logger.info(f"🧪 开始评估诊断结果")
            
            # 评估概念理解
            concept_score = self._evaluate_concepts(student_responses.get("concepts", {}))
            
            # 评估编程能力
            coding_score = self._evaluate_coding(student_responses.get("coding", {}))
            
            # 评估工具熟悉度
            tool_familiarity_score, skill_scores = self._evaluate_tools(student_responses.get("tools", {}))
            
            # 分析学习偏好
            preferences = self._analyze_preferences(student_responses.get("preferences", {}))
            
            # 生成综合评估结果
            results = {
                "concept_score": concept_score,
                "coding_score": coding_score,  
                "tool_familiarity": tool_familiarity_score,
                "skill_scores": skill_scores,
                "learning_style_preference": preferences["learning_style"],
                "time_budget_hours_per_week": preferences["time_budget"],
                "interests": preferences["interests"],
                "goals": preferences["goals"],
                "challenges": preferences["challenges"],
                "overall_readiness": self._calculate_overall_readiness(
                    concept_score, coding_score, tool_familiarity_score
                ),
                "recommendations": self._generate_initial_recommendations(
                    concept_score, coding_score, tool_familiarity_score, preferences
                ),
                "evaluated_at": datetime.now().isoformat()
            }
            
            logger.info(f"🧪 ✅ 诊断评估完成，整体准备度: {results['overall_readiness']}")
            return results
            
        except Exception as e:
            logger.error(f"🧪 ❌ 诊断评估失败: {str(e)}")
            raise DiagnosticServiceError(f"诊断评估失败: {str(e)}")
    
    def _evaluate_concepts(self, concept_responses: Dict[str, Any]) -> int:
        """评估概念理解得分"""
        total_score = 0
        max_score = 0
        
        # 从JSON数据中获取概念测试题目
        concepts_section = next((s for s in self.diagnostic_data["sections"] if s["id"] == "concepts"), None)
        if not concepts_section:
            logger.warning("未找到概念测试题目")
            return 0
            
        for question in concepts_section["questions"]:
            max_score += question["weight"]
            student_answer = concept_responses.get(question["id"])
            
            if question["type"] == "multiple_choice":
                if student_answer == question["correct_answer"]:
                    total_score += question["weight"]
                    logger.info(f"  ✅ {question['id']}: 选择题答对 +{question['weight']}分")
                else:
                    logger.info(f"  ❌ {question['id']}: 选择题答错")
            elif question["type"] == "short_answer":
                # AI智能评分或关键词匹配评分
                if student_answer:
                    score = self._score_short_answer(
                        student_answer, 
                        question["sample_answer"],
                        question_text=question.get("question", "")
                    )
                    earned = int(question["weight"] * score)
                    total_score += earned
                    logger.info(f"  {'✅' if score > 0.6 else '⚠️'} {question['id']}: 简答题 +{earned}/{question['weight']}分")
                else:
                    logger.info(f"  ⚠️ {question['id']}: 未作答")
        
        return int((total_score / max_score) * 100) if max_score > 0 else 0
    
    def _evaluate_coding(self, coding_responses: Dict[str, Any]) -> int:
        """评估编程能力得分"""
        total_score = 0
        max_score = 0
        
        # 从JSON数据中获取编程测试题目
        coding_section = next((s for s in self.diagnostic_data["sections"] if s["id"] == "coding"), None)
        if not coding_section:
            logger.warning("未找到编程测试题目")
            return 0
            
        for question in coding_section["questions"]:
            max_score += question["weight"]
            student_answer = coding_responses.get(question["id"])
            
            if question["type"] == "coding":
                if student_answer:
                    # AI智能评分或简化代码评估
                    score = self._score_coding_answer(student_answer, question)
                    earned = int(question["weight"] * score)
                    total_score += earned
                    logger.info(f"  {'✅' if score > 0.6 else '⚠️'} {question['id']}: 编程题 +{earned}/{question['weight']}分")
                else:
                    logger.info(f"  ⚠️ {question['id']}: 未提交代码")
            elif question["type"] == "code_analysis":
                if student_answer:
                    score = self._score_analysis_answer(student_answer, question)
                    earned = int(question["weight"] * score)
                    total_score += earned
                    logger.info(f"  {'✅' if score > 0.6 else '⚠️'} {question['id']}: 代码分析题 +{earned}/{question['weight']}分")
                else:
                    logger.info(f"  ⚠️ {question['id']}: 未作答")
        
        return int((total_score / max_score) * 100) if max_score > 0 else 0
    
    def _evaluate_tools(self, tool_responses: Dict[str, Any]) -> tuple[int, Dict[str, int]]:
        """评估工具熟悉度"""
        skill_scores = {}
        category_scores = []
        
        # 从JSON数据中获取工具调查
        tools_section = next((s for s in self.diagnostic_data["sections"] if s["id"] == "tools"), None)
        if not tools_section:
            logger.warning("未找到工具调查数据")
            return 0, {}
            
        for category in tools_section["survey"]:
            category_name = category["category"]
            category_total = 0
            tool_count = len(category["tools"])
            
            for tool in category["tools"]:
                tool_name = tool["name"]
                # 学生对工具的熟悉度评分（1-5）
                familiarity = tool_responses.get(tool_name, 1)
                skill_scores[tool_name] = familiarity * 20  # 转换为百分制
                category_total += familiarity
            
            # 计算类别平均分
            if tool_count > 0:
                category_avg = (category_total / tool_count) * 20
                category_scores.append(category_avg)
        
        # 计算总体工具熟悉度
        overall_score = int(sum(category_scores) / len(category_scores)) if category_scores else 0
        
        return overall_score, skill_scores
    
    def _analyze_preferences(self, preference_responses: Dict[str, Any]) -> Dict[str, Any]:
        """分析学习偏好"""
        return {
            "learning_style": preference_responses.get("learning_style", "examples_first"),
            "time_budget": preference_responses.get("time_budget", 6),
            "interests": preference_responses.get("interests", []),
            "goals": preference_responses.get("goals", []),
            "challenges": preference_responses.get("challenges", "concepts")
        }
    
    def _score_short_answer(self, student_answer: str, sample_answer: str, question_text: str = "") -> float:
        """
        简答题评分（优先使用AI评分）
        
        Args:
            student_answer: 学生答案
            sample_answer: 参考答案
            question_text: 题目内容（用于AI评分）
            
        Returns:
            0.0-1.0之间的得分率
        """
        if not student_answer:
            return 0.0
        
        # 尝试使用AI评分
        if self.ai_scoring.is_enabled() and question_text:
            try:
                result = self.ai_scoring.score_short_answer(
                    question=question_text,
                    student_answer=student_answer,
                    reference_answer=sample_answer,
                    max_score=100
                )
                score_rate = result['score'] / 100.0
                logger.info(f"  📝 AI评分: {result['score']}/100 - {result['feedback']}")
                return score_rate
            except Exception as e:
                logger.warning(f"  ⚠️ AI评分失败，使用规则评分: {str(e)}")
        
        # 备用：简单的关键词匹配
        student_words = set(student_answer.lower().split())
        sample_words = set(sample_answer.lower().split())
        
        # 计算词汇重叠度
        common_words = student_words.intersection(sample_words)
        if len(sample_words) == 0:
            return 0.0
        
        similarity = len(common_words) / len(sample_words)
        score_rate = min(similarity * 1.2, 1.0)
        logger.info(f"  📝 规则评分: {int(score_rate * 100)}/100")
        return score_rate
    
    def _score_coding_answer(self, student_code: str, question: Dict[str, Any]) -> float:
        """
        编程题评分（优先使用AI评分）
        
        Args:
            student_code: 学生代码
            question: 题目信息
            
        Returns:
            0.0-1.0之间的得分率
        """
        if not student_code:
            return 0.0
        
        # 尝试使用AI评分
        if self.ai_scoring.is_enabled():
            try:
                requirements = question.get("evaluation_criteria", [
                    "代码功能正确",
                    "代码结构清晰", 
                    "包含必要的错误处理"
                ])
                
                result = self.ai_scoring.score_coding_question(
                    question=question.get("question", ""),
                    student_code=student_code,
                    requirements=requirements,
                    max_score=100
                )
                score_rate = result['score'] / 100.0
                logger.info(f"  💻 AI评分: {result['score']}/100 - {result['feedback']}")
                return score_rate
            except Exception as e:
                logger.warning(f"  ⚠️ AI评分失败，使用规则评分: {str(e)}")
        
        # 备用：基础结构检查
        score = 0.0
        
        # 基础结构检查
        if "def " in student_code:
            score += 0.3
        if "return " in student_code:
            score += 0.3
        
        # 关键逻辑检查（根据题目类型）
        if question["id"] == "code_1":  # 查找最大值
            if "max(" in student_code or ">" in student_code:
                score += 0.4
        elif question["id"] == "code_2":  # API调用和错误处理
            if "try:" in student_code or "except" in student_code:
                score += 0.2
            if "requests." in student_code:
                score += 0.2
        
        logger.info(f"  💻 规则评分: {int(score * 100)}/100")
        return min(score, 1.0)
    
    def _score_analysis_answer(self, student_answer: str, question: Dict[str, Any]) -> float:
        """
        代码分析题评分（优先使用AI评分）
        
        Args:
            student_answer: 学生的分析
            question: 题目信息
            
        Returns:
            0.0-1.0之间的得分率
        """
        if not student_answer:
            return 0.0
        
        # 尝试使用AI评分
        if self.ai_scoring.is_enabled():
            try:
                result = self.ai_scoring.score_code_analysis(
                    question=question.get("question", ""),
                    code_snippet=question.get("code", ""),
                    student_analysis=student_answer,
                    max_score=100
                )
                score_rate = result['score'] / 100.0
                logger.info(f"  🔍 AI评分: {result['score']}/100 - {result['feedback']}")
                return score_rate
            except Exception as e:
                logger.warning(f"  ⚠️ AI评分失败，使用规则评分: {str(e)}")
        
        # 备用：简化评分，检查关键概念
        key_concepts = ["引用", "列表", "append", "修改", "同一个对象"]
        score = 0.0
        
        for concept in key_concepts:
            if concept in student_answer:
                score += 0.2
        
        logger.info(f"  🔍 规则评分: {int(score * 100)}/100")
        return min(score, 1.0)
    
    def _calculate_overall_readiness(self, concept_score: int, coding_score: int, tool_score: int) -> str:
        """计算整体准备度等级"""
        avg_score = (concept_score + coding_score + tool_score) / 3
        
        if avg_score >= 85:
            return "优秀"
        elif avg_score >= 70:
            return "良好"
        elif avg_score >= 50:
            return "合格"
        else:
            return "需要加强"
    
    def _generate_initial_recommendations(
        self, 
        concept_score: int, 
        coding_score: int, 
        tool_score: int,
        preferences: Dict[str, Any]
    ) -> List[str]:
        """生成初始建议"""
        recommendations = []
        
        # 基于得分的建议
        if concept_score < 60:
            recommendations.append("建议先复习基础技术概念，特别是API、HTTP等网络基础知识")
        
        if coding_score < 60:
            recommendations.append("建议加强编程基础练习，重点关注Python语法和错误处理")
        
        if tool_score < 60:
            recommendations.append("建议先熟悉开发环境和基础工具，如Git、命令行等")
        
        # 基于学习挑战的建议
        challenge = preferences.get("challenges", "")
        if challenge == "debugging":
            recommendations.append("推荐使用IDE调试功能，多练习错误定位技巧")
        elif challenge == "time_management":
            recommendations.append("建议制定详细的学习计划，设置阶段性目标")
        elif challenge == "motivation":
            recommendations.append("建议选择与个人兴趣相关的项目进行实践")
        
        # 基于兴趣的建议
        interests = preferences.get("interests", [])
        if "RAG" in interests:
            recommendations.append("可以重点关注RAG系统构建，这与你的兴趣匹配")
        if "移动端" in interests:
            recommendations.append("建议在UI设计和前端开发环节投入更多精力")
        
        if not recommendations:
            recommendations.append("你的基础不错，可以按标准路径学习，适当挑战高难度任务")
        
        return recommendations


class DiagnosticServiceError(Exception):
    """诊断服务错误"""
    pass
