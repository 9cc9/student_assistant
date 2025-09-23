"""入学诊断服务 - 生成学生画像的核心服务"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from ..models.student import StudentProfile, LearningLevel, LearningStyle

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
        self.concept_questions = self._init_concept_questions()
        self.coding_questions = self._init_coding_questions()  
        self.tool_survey = self._init_tool_survey()
        self.learning_preference_survey = self._init_learning_preference_survey()
        logger.info("🧪 诊断服务已初始化")
    
    def _init_concept_questions(self) -> List[Dict[str, Any]]:
        """初始化概念测试题目"""
        return [
            {
                "id": "concept_1",
                "question": "什么是API？",
                "type": "multiple_choice",
                "options": [
                    "A. 应用程序编程接口，用于不同软件组件之间的通信",
                    "B. 一种编程语言",
                    "C. 数据库管理系统",
                    "D. 网页设计工具"
                ],
                "correct_answer": "A",
                "weight": 10
            },
            {
                "id": "concept_2", 
                "question": "HTTP协议中，GET和POST请求的主要区别是什么？",
                "type": "multiple_choice",
                "options": [
                    "A. GET用于获取数据，POST用于提交数据",
                    "B. GET更安全，POST不安全",
                    "C. 没有区别，可以互换使用",
                    "D. GET只能在浏览器中使用"
                ],
                "correct_answer": "A",
                "weight": 10
            },
            {
                "id": "concept_3",
                "question": "什么是RAG（检索增强生成）？",
                "type": "multiple_choice", 
                "options": [
                    "A. 一种数据库技术",
                    "B. 结合信息检索和文本生成的AI技术",
                    "C. 网页前端框架",
                    "D. 版本控制工具"
                ],
                "correct_answer": "B",
                "weight": 15
            },
            {
                "id": "concept_4",
                "question": "Docker的主要作用是什么？",
                "type": "multiple_choice",
                "options": [
                    "A. 代码编辑器",
                    "B. 容器化平台，用于应用部署和环境管理",
                    "C. 数据库软件",
                    "D. 测试工具"
                ],
                "correct_answer": "B",
                "weight": 10
            },
            {
                "id": "concept_5",
                "question": "在Web开发中，前端和后端的主要职责分别是什么？",
                "type": "short_answer",
                "sample_answer": "前端负责用户界面和用户体验，后端负责数据处理、业务逻辑和服务器管理",
                "weight": 15
            }
        ]
    
    def _init_coding_questions(self) -> List[Dict[str, Any]]:
        """初始化编程测试题目"""
        return [
            {
                "id": "code_1",
                "question": "编写一个Python函数，接受一个列表作为参数，返回列表中的最大值",
                "type": "coding",
                "template": "def find_max(numbers):\n    # 在这里编写代码\n    pass",
                "test_cases": [
                    {"input": "[1, 2, 3, 4, 5]", "expected": "5"},
                    {"input": "[-1, -2, -3]", "expected": "-1"},
                    {"input": "[0]", "expected": "0"}
                ],
                "weight": 15
            },
            {
                "id": "code_2",
                "question": "编写一个函数，从网络API获取数据并处理错误",
                "type": "coding",
                "template": "import requests\n\ndef fetch_data(url):\n    # 在这里编写代码\n    # 需要处理可能的异常\n    pass",
                "evaluation_criteria": [
                    "使用try-catch处理异常",
                    "检查HTTP状态码",
                    "返回适当的数据格式"
                ],
                "weight": 20
            },
            {
                "id": "code_3", 
                "question": "解释以下代码的输出结果，并说明原因",
                "type": "code_analysis",
                "code": "x = [1, 2, 3]\ny = x\ny.append(4)\nprint(x)",
                "weight": 10
            }
        ]
    
    def _init_tool_survey(self) -> List[Dict[str, Any]]:
        """初始化工具熟悉度调查"""
        return [
            {
                "category": "编程基础",
                "tools": [
                    {"name": "Python", "description": "Python编程语言"},
                    {"name": "JavaScript", "description": "JavaScript编程语言"},
                    {"name": "Git", "description": "版本控制工具"},
                    {"name": "命令行/Terminal", "description": "命令行界面操作"}
                ]
            },
            {
                "category": "Web开发",
                "tools": [
                    {"name": "HTML/CSS", "description": "网页结构和样式"},
                    {"name": "React/Vue", "description": "前端框架"},
                    {"name": "Node.js", "description": "JavaScript运行环境"},
                    {"name": "REST API", "description": "RESTful接口设计"}
                ]
            },
            {
                "category": "AI/ML工具", 
                "tools": [
                    {"name": "OpenAI API", "description": "大语言模型API"},
                    {"name": "LangChain", "description": "LLM应用开发框架"},
                    {"name": "向量数据库", "description": "如FAISS、Pinecone等"},
                    {"name": "Jupyter Notebook", "description": "交互式编程环境"}
                ]
            },
            {
                "category": "部署运维",
                "tools": [
                    {"name": "Docker", "description": "容器化技术"},
                    {"name": "云服务", "description": "AWS、阿里云等云平台"},
                    {"name": "Linux", "description": "Linux操作系统"},
                    {"name": "数据库", "description": "MySQL、PostgreSQL等"}
                ]
            }
        ]
    
    def _init_learning_preference_survey(self) -> List[Dict[str, Any]]:
        """初始化学习偏好调查"""
        return [
            {
                "id": "learning_style",
                "question": "你更偏向哪种学习方式？",
                "type": "single_choice",
                "options": [
                    {"value": "examples_first", "label": "先看示例和案例，再学理论"},
                    {"value": "theory_first", "label": "先学理论基础，再看实践应用"},
                    {"value": "hands_on", "label": "直接动手实践，边做边学"},
                    {"value": "visual", "label": "通过图表、视频等可视化方式学习"}
                ]
            },
            {
                "id": "time_budget",
                "question": "你每周可以投入多少时间学习？",
                "type": "single_choice",
                "options": [
                    {"value": 3, "label": "每周3小时以下"},
                    {"value": 6, "label": "每周3-6小时"},
                    {"value": 10, "label": "每周6-10小时"},
                    {"value": 15, "label": "每周10小时以上"}
                ]
            },
            {
                "id": "interests",
                "question": "你对以下哪些领域感兴趣？（可多选）",
                "type": "multiple_choice",
                "options": [
                    {"value": "RAG", "label": "智能问答和知识检索"},
                    {"value": "Agent", "label": "AI智能体和自动化"},
                    {"value": "移动端", "label": "移动应用开发"},
                    {"value": "Web开发", "label": "网页和Web应用"},
                    {"value": "机器学习", "label": "机器学习和深度学习"},
                    {"value": "数据分析", "label": "数据分析和可视化"}
                ]
            },
            {
                "id": "goals",
                "question": "你希望通过这门课程达到什么目标？（可多选）",
                "type": "multiple_choice", 
                "options": [
                    {"value": "完成RAG应用", "label": "独立开发RAG应用"},
                    {"value": "掌握全栈开发", "label": "掌握前后端全栈技能"},
                    {"value": "参加竞赛", "label": "参与相关技术竞赛"},
                    {"value": "提升就业竞争力", "label": "增强就业竞争力"},
                    {"value": "个人项目", "label": "完成个人兴趣项目"},
                    {"value": "深入AI技术", "label": "深入理解AI技术原理"}
                ]
            },
            {
                "id": "challenges",
                "question": "你在学习编程时最大的挑战是什么？",
                "type": "single_choice",
                "options": [
                    {"value": "debugging", "label": "调试和错误定位"},
                    {"value": "concepts", "label": "理解复杂的概念"},
                    {"value": "time_management", "label": "时间管理和进度安排"},
                    {"value": "motivation", "label": "保持学习动力"},
                    {"value": "practical_application", "label": "将理论应用到实践"}
                ]
            }
        ]
    
    def get_diagnostic_test(self) -> Dict[str, Any]:
        """
        获取完整的入学诊断测试
        
        返回包含所有测试题目和调查问卷的结构化数据
        """
        return {
            "test_info": {
                "title": "AI课程入学诊断测试",
                "description": "通过这个测试，我们将了解你的技术基础和学习偏好，为你推荐最适合的学习路径",
                "estimated_time": "10-15分钟",
                "sections": 4
            },
            "sections": [
                {
                    "id": "concepts",
                    "title": "基础概念测试",
                    "description": "测试你对关键技术概念的理解",
                    "questions": self.concept_questions,
                    "time_limit": 300  # 5分钟
                },
                {
                    "id": "coding", 
                    "title": "编程能力测试",
                    "description": "通过简单的编程题目评估你的编程技能",
                    "questions": self.coding_questions,
                    "time_limit": 480  # 8分钟
                },
                {
                    "id": "tools",
                    "title": "工具熟悉度调查",
                    "description": "了解你对各种开发工具的熟悉程度",
                    "survey": self.tool_survey,
                    "time_limit": 120  # 2分钟
                },
                {
                    "id": "preferences",
                    "title": "学习偏好调查", 
                    "description": "了解你的学习风格和目标",
                    "questions": self.learning_preference_survey,
                    "time_limit": 120  # 2分钟
                }
            ]
        }
    
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
        
        for question in self.concept_questions:
            max_score += question["weight"]
            student_answer = concept_responses.get(question["id"])
            
            if question["type"] == "multiple_choice":
                if student_answer == question["correct_answer"]:
                    total_score += question["weight"]
            elif question["type"] == "short_answer":
                # 简单的关键词匹配评分
                if student_answer:
                    score = self._score_short_answer(student_answer, question["sample_answer"])
                    total_score += int(question["weight"] * score)
        
        return int((total_score / max_score) * 100) if max_score > 0 else 0
    
    def _evaluate_coding(self, coding_responses: Dict[str, Any]) -> int:
        """评估编程能力得分"""
        total_score = 0
        max_score = 0
        
        for question in self.coding_questions:
            max_score += question["weight"]
            student_answer = coding_responses.get(question["id"])
            
            if question["type"] == "coding":
                if student_answer:
                    # 简化的代码评估：检查关键词和结构
                    score = self._score_coding_answer(student_answer, question)
                    total_score += int(question["weight"] * score)
            elif question["type"] == "code_analysis":
                if student_answer:
                    score = self._score_analysis_answer(student_answer, question)
                    total_score += int(question["weight"] * score)
        
        return int((total_score / max_score) * 100) if max_score > 0 else 0
    
    def _evaluate_tools(self, tool_responses: Dict[str, Any]) -> tuple[int, Dict[str, int]]:
        """评估工具熟悉度"""
        skill_scores = {}
        category_scores = []
        
        for category in self.tool_survey:
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
    
    def _score_short_answer(self, student_answer: str, sample_answer: str) -> float:
        """简单的短答题评分"""
        student_words = set(student_answer.lower().split())
        sample_words = set(sample_answer.lower().split())
        
        # 计算词汇重叠度
        common_words = student_words.intersection(sample_words)
        if len(sample_words) == 0:
            return 0.0
        
        similarity = len(common_words) / len(sample_words)
        return min(similarity * 1.2, 1.0)  # 稍微加权，最高不超过1.0
    
    def _score_coding_answer(self, student_code: str, question: Dict[str, Any]) -> float:
        """简化的代码评分"""
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
        
        return min(score, 1.0)
    
    def _score_analysis_answer(self, student_answer: str, question: Dict[str, Any]) -> float:
        """代码分析题评分"""
        # 简化评分：检查是否提到关键概念
        key_concepts = ["引用", "列表", "append", "修改", "同一个对象"]
        score = 0.0
        
        for concept in key_concepts:
            if concept in student_answer:
                score += 0.2
        
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
