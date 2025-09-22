"""Idea评估器"""
from typing import Dict, List, Any
import logging

from .base import BaseEvaluator, EvaluatorError
from ..models.assessment import IdeaScore
from ..config.settings import get_prompts


logger = logging.getLogger(__name__)


class IdeaEvaluator(BaseEvaluator):
    """创意想法评估器"""
    
    def __init__(self):
        super().__init__()
        self.prompts = get_prompts()
    
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估学生的创意想法
        
        Args:
            data: 包含创意信息的字典
                - idea_text: 创意描述
                - technical_stack: 技术栈
                - target_users: 目标用户
                - core_features: 核心功能
                
        Returns:
            评估结果字典
        """
        try:
            # 提取数据
            idea_text = data.get("idea_text", "")
            technical_stack = data.get("technical_stack", [])
            target_users = data.get("target_users", "")
            core_features = data.get("core_features", [])
            
            if not idea_text:
                raise EvaluatorError("缺少创意描述文本")
            
            # 格式化提示词
            prompt = f"""
请对以下项目创意进行评估，必须严格按照JSON格式返回结果，不要添加任何额外文字：

项目描述: {idea_text}
技术栈: {", ".join(technical_stack) if technical_stack else "未指定"}
目标用户: {target_users or "未指定"}
核心功能: {", ".join(core_features) if core_features else "未指定"}

请从以下维度进行评估（每个维度0-100分）：

1. 创新性 (innovation): 技术新颖度、解决方案独特性
2. 可行性 (feasibility): 技术难度、开发周期、资源需求
3. 学习价值 (learning_value): 技能提升程度、知识拓展范围

请严格按照以下JSON格式返回（不要添加任何解释）：
{{
    "innovation": 数字评分,
    "feasibility": 数字评分,
    "learning_value": 数字评分,
    "feedback": "详细反馈文字",
    "suggestions": ["建议1", "建议2"],
    "resources": ["推荐资源1", "推荐资源2"]
}}
"""
            
            # 调用AI进行评估
            logger.info("开始评估创意想法...")
            response = await self._call_ai_api(prompt, max_tokens=1500)
            
            try:
                result = self._parse_json_response(response)
            except Exception as e:
                logger.error(f"Idea评估响应解析失败: {str(e)}")
                # 返回默认评估结果
                result = {
                    "innovation": 70,
                    "feasibility": 70,
                    "learning_value": 70,
                    "feedback": "AI响应解析失败，给予默认评分",
                    "suggestions": ["请完善项目描述"],
                    "resources": ["创新思维训练"]
                }
            
            # 验证和处理评分
            innovation_score = self._validate_score(result.get("innovation", 0))
            feasibility_score = self._validate_score(result.get("feasibility", 0))
            learning_value_score = self._validate_score(result.get("learning_value", 0))
            
            idea_score = IdeaScore(
                innovation=innovation_score,
                feasibility=feasibility_score,
                learning_value=learning_value_score
            )
            
            # 生成诊断信息
            feedback = result.get("feedback", "")
            suggestions = result.get("suggestions", [])
            issues = self._extract_issues_from_feedback(feedback, idea_score)
            
            diagnoses = []
            if innovation_score < 70:
                diagnoses.extend(self._generate_diagnosis(
                    "idea.innovation",
                    ["创新性有待提升"],
                    ["考虑引入更多前沿技术或独特功能"]
                ))
            
            if feasibility_score < 70:
                diagnoses.extend(self._generate_diagnosis(
                    "idea.feasibility", 
                    ["可行性存在问题"],
                    ["重新评估技术难度和资源需求"]
                ))
            
            if learning_value_score < 70:
                diagnoses.extend(self._generate_diagnosis(
                    "idea.learning_value",
                    ["学习价值偏低"],
                    ["增加技能挑战性或知识拓展性"]
                ))
            
            # 推荐学习资源
            resources = self._recommend_resources(idea_score, suggestions)
            
            logger.info(f"Idea评估完成，总分: {idea_score.overall}")
            
            return {
                "score": idea_score,
                "overall_score": idea_score.overall,
                "diagnoses": diagnoses,
                "resources": resources,
                "feedback": feedback,
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"Idea评估失败: {str(e)}")
            raise EvaluatorError(f"Idea评估失败: {str(e)}")
    
    def _extract_issues_from_feedback(self, feedback: str, score: IdeaScore) -> List[str]:
        """从反馈中提取问题"""
        issues = []
        
        if score.innovation < 60:
            issues.append("创意缺乏新颖性")
        elif score.innovation < 80:
            issues.append("创意创新程度一般")
            
        if score.feasibility < 60:
            issues.append("技术实现可行性低")
        elif score.feasibility < 80:
            issues.append("技术实现存在一定挑战")
            
        if score.learning_value < 60:
            issues.append("学习价值不足")
        elif score.learning_value < 80:
            issues.append("学习价值有待提升")
            
        return issues
    
    def _recommend_resources(self, score: IdeaScore, suggestions: List[str]) -> List[str]:
        """推荐学习资源"""
        resources = []
        
        if score.innovation < 80:
            resources.extend([
                "创新思维与设计思维课程",
                "前沿技术趋势报告",
                "优秀产品创意案例库"
            ])
        
        if score.feasibility < 80:
            resources.extend([
                "技术可行性分析方法",
                "项目规划与管理指南",
                "技术选型最佳实践"
            ])
        
        if score.learning_value < 80:
            resources.extend([
                "技能提升路径规划",
                "学习目标设定方法",
                "知识体系构建指南"
            ])
        
        return list(set(resources))  # 去重


class IdeaValidationError(EvaluatorError):
    """创意验证错误"""
    pass


