#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI智能评分服务

使用通义千问大语言模型对诊断测试中的主观题进行智能评分
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from ..config.settings import AIConfig

logger = logging.getLogger(__name__)


class AIScoringServiceError(Exception):
    """AI评分服务异常"""
    pass


class AIScoringService:
    """
    AI智能评分服务类
    
    负责使用LLM对简答题、编程题等主观题进行智能评分
    """
    
    def __init__(self):
        # 从统一配置中读取
        self.ai_config = AIConfig()
        self.api_key = self.ai_config.dashscope_api_key
        self.model = self.ai_config.qwen_model
        self.enabled = bool(self.api_key) and self.api_key != ""
        
        if not self.enabled:
            logger.warning("⚠️ dashscope_api_key 未配置，AI评分功能将禁用，使用规则评分")
        else:
            logger.info(f"✅ AI评分服务已启用，使用模型: {self.model}")
    
    def is_enabled(self) -> bool:
        """检查AI评分是否启用"""
        return self.enabled
    
    def score_short_answer(
        self, 
        question: str, 
        student_answer: str, 
        reference_answer: str,
        max_score: int = 100
    ) -> Dict[str, Any]:
        """
        AI评分简答题
        
        Args:
            question: 题目内容
            student_answer: 学生答案
            reference_answer: 参考答案
            max_score: 满分
            
        Returns:
            包含分数、评语和详细分析的字典
        """
        if not self.enabled:
            return self._fallback_score_short_answer(student_answer, reference_answer, max_score)
        
        try:
            prompt = self._build_short_answer_prompt(
                question, student_answer, reference_answer, max_score
            )
            
            response = self._call_qwen_api(prompt)
            result = self._parse_scoring_response(response, max_score)
            
            logger.info(f"✅ 简答题AI评分完成: {result['score']}/{max_score}分")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI评分失败，使用备用评分: {str(e)}")
            return self._fallback_score_short_answer(student_answer, reference_answer, max_score)
    
    def score_coding_question(
        self,
        question: str,
        student_code: str,
        requirements: list[str],
        max_score: int = 100
    ) -> Dict[str, Any]:
        """
        AI评分编程题
        
        Args:
            question: 题目内容
            student_code: 学生代码
            requirements: 评分要求列表
            max_score: 满分
            
        Returns:
            包含分数、评语和详细分析的字典
        """
        if not self.enabled:
            return self._fallback_score_coding(student_code, max_score)
        
        try:
            prompt = self._build_coding_prompt(
                question, student_code, requirements, max_score
            )
            
            response = self._call_qwen_api(prompt)
            result = self._parse_scoring_response(response, max_score)
            
            logger.info(f"✅ 编程题AI评分完成: {result['score']}/{max_score}分")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI评分失败，使用备用评分: {str(e)}")
            return self._fallback_score_coding(student_code, max_score)
    
    def score_code_analysis(
        self,
        question: str,
        code_snippet: str,
        student_analysis: str,
        max_score: int = 100
    ) -> Dict[str, Any]:
        """
        AI评分代码分析题
        
        Args:
            question: 题目内容
            code_snippet: 要分析的代码
            student_analysis: 学生的分析
            max_score: 满分
            
        Returns:
            包含分数、评语和详细分析的字典
        """
        if not self.enabled:
            return self._fallback_score_analysis(student_analysis, max_score)
        
        try:
            prompt = self._build_code_analysis_prompt(
                question, code_snippet, student_analysis, max_score
            )
            
            response = self._call_qwen_api(prompt)
            result = self._parse_scoring_response(response, max_score)
            
            logger.info(f"✅ 代码分析题AI评分完成: {result['score']}/{max_score}分")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI评分失败，使用备用评分: {str(e)}")
            return self._fallback_score_analysis(student_analysis, max_score)
    
    def _build_short_answer_prompt(
        self, 
        question: str, 
        student_answer: str, 
        reference_answer: str,
        max_score: int
    ) -> str:
        """构建简答题评分提示词"""
        return f"""你是一位专业的AI课程教师，负责评估学生的简答题答案。

【题目】
{question}

【参考答案】
{reference_answer}

【学生答案】
{student_answer}

【评分标准】
- 满分：{max_score}分
- 评分要点：
  1. 答案的准确性（40%）
  2. 概念理解的深度（30%）
  3. 表达的清晰度（20%）
  4. 知识点的完整性（10%）

【评分要求】
请你作为专业教师，对学生答案进行评分，并以JSON格式返回结果：

{{
    "score": 85,  // 0-{max_score}之间的整数
    "feedback": "答案总体正确，概念理解清晰...",  // 50字以内的简短评语
    "strengths": ["正确理解了API的定义", "举例说明很恰当"],  // 优点列表
    "improvements": ["可以补充说明RESTful API的特点"]  // 改进建议列表
}}

只返回JSON，不要其他内容。"""
    
    def _build_coding_prompt(
        self,
        question: str,
        student_code: str,
        requirements: list[str],
        max_score: int
    ) -> str:
        """构建编程题评分提示词"""
        requirements_text = "\n  ".join([f"{i+1}. {req}" for i, req in enumerate(requirements)])
        
        return f"""你是一位专业的编程教师，负责评估学生的编程作业。

【题目】
{question}

【学生代码】
```python
{student_code}
```

【评分要点】
{requirements_text}

【评分标准】
- 满分：{max_score}分
- 代码正确性（50%）
- 代码规范性（20%）
- 算法效率（15%）
- 异常处理（15%）

【评分要求】
请你作为专业教师，对学生代码进行评分，并以JSON格式返回结果：

{{
    "score": 75,  // 0-{max_score}之间的整数
    "feedback": "代码基本实现了功能...",  // 50字以内的简短评语
    "strengths": ["函数结构清晰", "使用了合适的内置函数"],  // 优点列表
    "improvements": ["缺少边界条件检查", "建议添加类型提示"],  // 改进建议列表
    "bugs": []  // 发现的bug列表，如果没有则为空数组
}}

只返回JSON，不要其他内容。"""
    
    def _build_code_analysis_prompt(
        self,
        question: str,
        code_snippet: str,
        student_analysis: str,
        max_score: int
    ) -> str:
        """构建代码分析题评分提示词"""
        return f"""你是一位专业的编程教师，负责评估学生对代码的理解和分析能力。

【题目】
{question}

【代码片段】
```python
{code_snippet}
```

【学生分析】
{student_analysis}

【评分标准】
- 满分：{max_score}分
- 输出结果预测准确性（40%）
- 原因解释的正确性（40%）
- 概念理解的深度（20%）

【评分要求】
请你作为专业教师，评估学生对代码的分析是否正确，并以JSON格式返回结果：

{{
    "score": 90,  // 0-{max_score}之间的整数
    "feedback": "分析准确，理解到位...",  // 50字以内的简短评语
    "strengths": ["正确理解了列表引用机制", "解释清晰"],  // 优点列表
    "improvements": ["可以进一步说明深拷贝和浅拷贝的区别"]  // 改进建议列表
}}

只返回JSON，不要其他内容。"""
    
    def _call_qwen_api(self, prompt: str) -> str:
        """调用通义千问API"""
        try:
            import dashscope
            from dashscope import Generation
            
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                api_key=self.api_key,
                result_format='message',
                max_tokens=500,
                temperature=0.3,  # 较低的温度以获得更稳定的评分
                top_p=0.8
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise AIScoringServiceError(f"API调用失败: {response.message}")
                
        except ImportError:
            raise AIScoringServiceError("dashscope库未安装，请运行: pip install dashscope")
        except Exception as e:
            raise AIScoringServiceError(f"API调用异常: {str(e)}")
    
    def _parse_scoring_response(self, response: str, max_score: int) -> Dict[str, Any]:
        """解析AI返回的评分结果"""
        try:
            # 尝试提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # 验证和规范化结果
                score = min(max(int(result.get('score', 0)), 0), max_score)
                
                return {
                    'score': score,
                    'feedback': result.get('feedback', ''),
                    'strengths': result.get('strengths', []),
                    'improvements': result.get('improvements', []),
                    'bugs': result.get('bugs', []),
                    'scored_by': 'AI',
                    'scored_at': datetime.now().isoformat()
                }
            else:
                raise ValueError("响应中未找到有效的JSON")
                
        except Exception as e:
            logger.error(f"❌ 解析AI响应失败: {str(e)}")
            logger.debug(f"原始响应: {response}")
            raise AIScoringServiceError(f"解析评分结果失败: {str(e)}")
    
    def _fallback_score_short_answer(
        self, 
        student_answer: str, 
        reference_answer: str,
        max_score: int
    ) -> Dict[str, Any]:
        """简答题的备用评分（基于关键词匹配）"""
        if not student_answer:
            return {
                'score': 0,
                'feedback': '未作答',
                'strengths': [],
                'improvements': ['请完成答题'],
                'scored_by': 'rule',
                'scored_at': datetime.now().isoformat()
            }
        
        # 简单的关键词匹配
        student_words = set(student_answer.lower().split())
        reference_words = set(reference_answer.lower().split())
        common_words = student_words.intersection(reference_words)
        
        if len(reference_words) == 0:
            similarity = 0.5
        else:
            similarity = min(len(common_words) / len(reference_words) * 1.2, 1.0)
        
        score = int(similarity * max_score)
        
        return {
            'score': score,
            'feedback': f'关键词匹配度: {int(similarity*100)}%',
            'strengths': ['已作答'] if score > 0 else [],
            'improvements': ['建议包含更多关键概念'] if score < max_score * 0.8 else [],
            'scored_by': 'rule',
            'scored_at': datetime.now().isoformat()
        }
    
    def _fallback_score_coding(self, student_code: str, max_score: int) -> Dict[str, Any]:
        """编程题的备用评分（基于代码模式匹配）"""
        if not student_code:
            return {
                'score': 0,
                'feedback': '未提交代码',
                'strengths': [],
                'improvements': ['请完成编程题'],
                'scored_by': 'rule',
                'scored_at': datetime.now().isoformat()
            }
        
        score = 0
        strengths = []
        improvements = []
        
        # 基础结构检查
        if "def " in student_code:
            score += int(max_score * 0.3)
            strengths.append("有函数定义")
        else:
            improvements.append("建议使用函数封装逻辑")
        
        if "return " in student_code:
            score += int(max_score * 0.3)
            strengths.append("有返回值")
        else:
            improvements.append("函数应返回结果")
        
        # 关键逻辑
        if "max(" in student_code or ">" in student_code:
            score += int(max_score * 0.4)
            strengths.append("使用了合适的逻辑")
        else:
            improvements.append("逻辑实现可以优化")
        
        return {
            'score': min(score, max_score),
            'feedback': '基于代码模式的自动评分',
            'strengths': strengths,
            'improvements': improvements,
            'scored_by': 'rule',
            'scored_at': datetime.now().isoformat()
        }
    
    def _fallback_score_analysis(self, student_analysis: str, max_score: int) -> Dict[str, Any]:
        """代码分析题的备用评分"""
        if not student_analysis:
            return {
                'score': 0,
                'feedback': '未作答',
                'strengths': [],
                'improvements': ['请完成代码分析'],
                'scored_by': 'rule',
                'scored_at': datetime.now().isoformat()
            }
        
        # 检查关键概念
        key_concepts = ["引用", "列表", "append", "修改", "对象", "指向"]
        found_concepts = [c for c in key_concepts if c in student_analysis]
        
        score = int((len(found_concepts) / len(key_concepts)) * max_score)
        
        return {
            'score': score,
            'feedback': f'提到了{len(found_concepts)}个关键概念',
            'strengths': [f'理解了{c}的概念' for c in found_concepts[:2]],
            'improvements': ['可以更详细地解释代码执行过程'] if score < max_score * 0.8 else [],
            'scored_by': 'rule',
            'scored_at': datetime.now().isoformat()
        }


# 创建全局单例
_ai_scoring_service = None


def get_ai_scoring_service() -> AIScoringService:
    """获取AI评分服务单例"""
    global _ai_scoring_service
    if _ai_scoring_service is None:
        _ai_scoring_service = AIScoringService()
    return _ai_scoring_service

