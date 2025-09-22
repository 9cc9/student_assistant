"""代码审查器"""
from typing import Dict, List, Any, Optional
import logging
import re
import asyncio
from urllib.parse import urlparse
import subprocess
import tempfile
import os
from pathlib import Path

from .base import BaseEvaluator, EvaluatorError
from ..models.assessment import CodeScore
from ..config.settings import get_prompts
from ..services.code_analyzer import EnhancedCodeAnalyzer


logger = logging.getLogger(__name__)


class CodeReviewer(BaseEvaluator):
    """代码审查器"""
    
    def __init__(self):
        super().__init__()
        self.prompts = get_prompts()
        self.code_analyzer = EnhancedCodeAnalyzer()
    
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估代码质量
        
        Args:
            data: 包含代码信息的字典
                - repo_url: 代码仓库链接
                - language: 主要编程语言
                - framework: 使用的框架
                - lines_of_code: 代码行数
                - test_coverage: 测试覆盖率
                - code_snippets: 代码片段
                
        Returns:
            评估结果字典
        """
        try:
            # 提取数据
            repo_url = data.get("code_repo", data.get("repo_url", ""))
            language = data.get("language", "未指定")
            framework = data.get("framework", "未指定")
            lines_of_code = data.get("lines_of_code", 0)
            test_coverage = data.get("test_coverage", 0.0)
            code_snippets = data.get("code_snippets", [])
            
            if not repo_url and not code_snippets:
                raise EvaluatorError("缺少代码仓库链接或代码片段")
            
            # 代码静态分析
            code_analysis = await self._analyze_code(repo_url, code_snippets, language)
            
            # 如果有完整项目路径，进行深度分析
            enhanced_analysis = None
            if repo_url and Path(repo_url).exists():
                try:
                    enhanced_analysis = await self.code_analyzer.analyze_project(repo_url)
                except Exception as e:
                    logger.warning(f"增强分析失败: {str(e)}")
            
            # 构建详细的提示词
            prompt = f"""
请对以下代码进行质量评估，必须严格按照JSON格式返回结果：

代码来源: {repo_url or "代码片段提交"}
编程语言: {language}
使用框架: {framework}
代码行数: {lines_of_code}
测试覆盖率: {test_coverage}%

代码分析结果: {code_analysis}

"""
            
            # 添加代码片段
            if code_snippets:
                prompt += "代码片段:\n"
                for i, snippet in enumerate(code_snippets[:3]):  # 最多分析前3个片段
                    prompt += f"\n片段{i+1}:\n```{language}\n{snippet[:500]}...\n```\n"
            
            prompt += """
请从以下维度评估（每个维度0-100分）：

1. 正确性 (correctness): 语法正确、逻辑完整、错误处理
2. 可读性 (readability): 命名规范、代码结构、注释质量  
3. 架构 (architecture): 模块化设计、设计模式、接口设计
4. 性能 (performance): 算法效率、资源使用、安全考虑

请严格按照以下JSON格式返回（不要添加任何解释）：
{
    "correctness": 数字评分,
    "readability": 数字评分,
    "architecture": 数字评分,
    "performance": 数字评分,
    "feedback": "详细反馈文字",
    "suggestions": ["建议1", "建议2"],
    "resources": ["推荐资源1", "推荐资源2"]
}
"""
            
            # 如果有增强分析，添加到提示词
            if enhanced_analysis:
                enhanced_prompt = self._build_enhanced_prompt(prompt, enhanced_analysis)
            else:
                enhanced_prompt = prompt
            
            # 调用AI进行评估
            logger.info("开始评估代码质量...")
            response = await self._call_ai_api(enhanced_prompt, max_tokens=2000)
            
            try:
                result = self._parse_json_response(response)
            except Exception as e:
                logger.error(f"代码评估响应解析失败: {str(e)}")
                # 返回默认评估结果
                result = {
                    "correctness": 70,
                    "readability": 70,
                    "architecture": 70,
                    "performance": 70,
                    "feedback": "AI响应解析失败，给予默认评分",
                    "suggestions": ["请检查代码质量"],
                    "resources": ["代码规范文档"]
                }
            
            # 验证和处理评分
            correctness_score = self._validate_score(result.get("correctness", 0))
            readability_score = self._validate_score(result.get("readability", 0))
            architecture_score = self._validate_score(result.get("architecture", 0))
            performance_score = self._validate_score(result.get("performance", 0))
            
            code_score = CodeScore(
                correctness=correctness_score,
                readability=readability_score,
                architecture=architecture_score,
                performance=performance_score
            )
            
            # 生成诊断信息
            feedback = result.get("feedback", "")
            suggestions = result.get("suggestions", [])
            issues = result.get("issues", [])
            
            diagnoses = self._generate_code_diagnoses(code_score, issues, test_coverage)
            
            # 推荐学习资源
            resources = self._recommend_code_resources(code_score, language, framework)
            
            logger.info(f"代码评估完成，总分: {code_score.overall}")
            
            return {
                "score": code_score,
                "overall_score": code_score.overall,
                "diagnoses": diagnoses,
                "resources": resources,
                "feedback": feedback,
                "code_analysis": code_analysis,
                "enhanced_analysis": enhanced_analysis,
                "issues": issues,
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"代码评估失败: {str(e)}")
            raise EvaluatorError(f"代码评估失败: {str(e)}")
    
    async def _analyze_code(self, repo_url: str, code_snippets: List[str], 
                           language: str) -> str:
        """
        分析代码
        
        Args:
            repo_url: 代码仓库链接
            code_snippets: 代码片段
            language: 编程语言
            
        Returns:
            代码分析结果
        """
        analysis_results = []
        
        # 分析代码片段
        if code_snippets:
            snippet_analysis = self._analyze_code_snippets(code_snippets, language)
            analysis_results.append(f"代码片段分析: {snippet_analysis}")
        
        # 如果有仓库链接，尝试进行更深入的分析
        if repo_url:
            repo_analysis = await self._analyze_repository(repo_url)
            if repo_analysis:
                analysis_results.append(f"仓库分析: {repo_analysis}")
        
        return "\n".join(analysis_results)
    
    def _analyze_code_snippets(self, code_snippets: List[str], language: str) -> str:
        """分析代码片段"""
        analysis = []
        
        for i, snippet in enumerate(code_snippets):
            snippet_analysis = []
            
            # 基本统计
            lines = snippet.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            snippet_analysis.append(f"行数: {len(non_empty_lines)}")
            
            # 注释率分析
            comment_lines = self._count_comment_lines(snippet, language)
            comment_ratio = comment_lines / len(non_empty_lines) if non_empty_lines else 0
            snippet_analysis.append(f"注释率: {comment_ratio:.1%}")
            
            # 复杂度分析（简化版）
            complexity = self._estimate_complexity(snippet)
            snippet_analysis.append(f"复杂度: {complexity}")
            
            # 命名规范检查
            naming_issues = self._check_naming_conventions(snippet, language)
            if naming_issues:
                snippet_analysis.append(f"命名问题: {len(naming_issues)}个")
            
            analysis.append(f"片段{i+1}: {', '.join(snippet_analysis)}")
        
        return "; ".join(analysis)
    
    async def _analyze_repository(self, repo_url: str) -> Optional[str]:
        """分析代码仓库（简化版）"""
        try:
            # 这里可以实现更复杂的仓库分析逻辑
            # 例如克隆仓库、运行静态分析工具等
            
            # 从URL推断一些信息
            parsed_url = urlparse(repo_url)
            if "github.com" in parsed_url.netloc:
                return "GitHub仓库，建议检查README、测试文件和CI配置"
            elif "gitlab.com" in parsed_url.netloc:
                return "GitLab仓库，建议检查项目结构和文档"
            else:
                return "代码仓库链接有效"
                
        except Exception as e:
            logger.warning(f"仓库分析失败: {str(e)}")
            return None
    
    def _count_comment_lines(self, code: str, language: str) -> int:
        """统计注释行数"""
        lines = code.split('\n')
        comment_count = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # 根据语言判断注释
            if language.lower() in ['python']:
                if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    comment_count += 1
            elif language.lower() in ['javascript', 'typescript', 'java', 'c++', 'c']:
                if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    comment_count += 1
            elif language.lower() in ['html']:
                if '<!--' in stripped:
                    comment_count += 1
        
        return comment_count
    
    def _estimate_complexity(self, code: str) -> str:
        """估算代码复杂度"""
        # 简化的复杂度评估
        complexity_keywords = [
            'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally',
            'switch', 'case', 'catch', 'loop'
        ]
        
        complexity_count = sum(code.lower().count(keyword) for keyword in complexity_keywords)
        
        if complexity_count < 3:
            return "低"
        elif complexity_count < 8:
            return "中等"
        else:
            return "高"
    
    def _check_naming_conventions(self, code: str, language: str) -> List[str]:
        """检查命名规范"""
        issues = []
        
        # 简化的命名检查
        if language.lower() == 'python':
            # 检查函数名是否使用snake_case
            func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            functions = re.findall(func_pattern, code)
            for func in functions:
                if not re.match(r'^[a-z_][a-z0-9_]*$', func):
                    issues.append(f"函数名 '{func}' 不符合snake_case规范")
        
        elif language.lower() in ['javascript', 'typescript']:
            # 检查函数名是否使用camelCase
            func_pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            functions = re.findall(func_pattern, code)
            for func in functions:
                if not re.match(r'^[a-z][a-zA-Z0-9]*$', func):
                    issues.append(f"函数名 '{func}' 不符合camelCase规范")
        
        return issues
    
    def _generate_code_diagnoses(self, score: CodeScore, issues: List[str], 
                                test_coverage: float) -> List:
        """生成代码诊断信息"""
        diagnoses = []
        
        if score.correctness < 70:
            diagnoses.extend(self._generate_diagnosis(
                "code.correctness",
                ["代码正确性和健壮性不足"] + issues[:2],
                ["增加单元测试，提高测试覆盖率至80%以上", "完善错误处理机制"]
            ))
        
        if score.readability < 70:
            diagnoses.extend(self._generate_diagnosis(
                "code.readability",
                ["代码可读性和可维护性有待提升"],
                ["改进变量和函数命名", "增加必要的代码注释", "重构复杂的代码结构"]
            ))
        
        if score.architecture < 70:
            diagnoses.extend(self._generate_diagnosis(
                "code.architecture",
                ["代码架构和设计模式使用不当"],
                ["采用合适的设计模式", "提高代码模块化程度", "改进接口设计"]
            ))
        
        if score.performance < 70:
            diagnoses.extend(self._generate_diagnosis(
                "code.performance",
                ["性能和安全性存在问题"],
                ["优化算法复杂度", "减少资源占用", "加强安全性检查"]
            ))
        
        # 测试覆盖率相关诊断
        if test_coverage < 80:
            diagnoses.extend(self._generate_diagnosis(
                "code.tests",
                [f"测试覆盖率偏低（当前{test_coverage}%）"],
                ["编写更多单元测试，目标覆盖率≥80%"]
            ))
        
        return diagnoses
    
    def _recommend_code_resources(self, score: CodeScore, language: str, 
                                 framework: str) -> List[str]:
        """推荐代码学习资源"""
        resources = []
        
        if score.correctness < 80:
            resources.extend([
                f"{language}单元测试最佳实践",
                "错误处理与异常管理指南",
                "代码调试技巧与工具"
            ])
        
        if score.readability < 80:
            resources.extend([
                f"{language}编码规范与风格指南",
                "代码重构技巧",
                "代码注释最佳实践"
            ])
        
        if score.architecture < 80:
            resources.extend([
                "设计模式实战教程",
                f"{language}项目架构设计",
                "软件架构原则与实践"
            ])
        
        if score.performance < 80:
            resources.extend([
                f"{language}性能优化指南",
                "算法与数据结构优化",
                "代码安全最佳实践"
            ])
        
        # 框架相关资源
        if framework and framework != "未指定":
            resources.append(f"{framework}框架最佳实践")
        
        return list(set(resources))  # 去重
    
    def _build_enhanced_prompt(self, base_prompt: str, enhanced_analysis: dict) -> str:
        """构建包含增强分析的提示词"""
        enhancement_text = "\n\n=== 深度代码分析结果 ===\n"
        
        # 添加整体指标
        metrics = enhanced_analysis.get("overall_metrics", {})
        if hasattr(metrics, 'lines_of_code'):
            enhancement_text += f"总代码行数: {metrics.lines_of_code}\n"
            enhancement_text += f"注释行数: {metrics.comment_lines}\n"
            enhancement_text += f"复杂度: {metrics.complexity}\n"
        
        # 添加架构分析
        arch = enhanced_analysis.get("architecture_analysis", {})
        if arch.get("structure_score"):
            enhancement_text += f"架构评分: {arch['structure_score']:.1f}/100\n"
            enhancement_text += f"模块化评分: {arch.get('modularity_score', 0):.1f}/100\n"
        
        # 添加最佳实践检查
        bp = enhanced_analysis.get("best_practices", {})
        if bp.get("score"):
            enhancement_text += f"最佳实践评分: {bp['score']:.1f}/100\n"
            checklist = bp.get("checklist", {})
            enhancement_text += f"项目文档完整性: {'是' if checklist.get('has_readme') else '否'}\n"
            enhancement_text += f"包含测试: {'是' if checklist.get('has_tests') else '否'}\n"
        
        # 添加主要问题
        issues = enhanced_analysis.get("issues", [])
        if issues:
            enhancement_text += f"\n发现的主要问题:\n"
            for issue in issues[:5]:  # 显示前5个问题
                if hasattr(issue, 'message'):
                    enhancement_text += f"- {issue.message} (严重程度: {issue.severity})\n"
        
        # 添加建议
        recommendations = enhanced_analysis.get("recommendations", [])
        if recommendations:
            enhancement_text += f"\n主要建议:\n"
            for rec in recommendations[:3]:  # 显示前3个建议
                enhancement_text += f"- {rec}\n"
        
        return base_prompt + enhancement_text + "\n\n请基于以上深度分析结果给出更准确的评估。"


class CodeAnalysisError(EvaluatorError):
    """代码分析错误"""
    pass


