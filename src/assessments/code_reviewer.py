"""代码审查器"""

import ast
import time
import subprocess
import os
import tempfile
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import requests
from urllib.parse import urlparse
import re

from .base import BaseEvaluator, EvaluationResult
from ..models import ScoreBreakdown, Diagnosis, ScoreDimension


class CodeReviewer(BaseEvaluator):
    """代码审查器 - 评估正确性、健壮性、可读性、可维护性、架构、性能、安全性"""
    
    WEIGHTS = {
        ScoreDimension.CODE_CORRECTNESS: 0.15,      # 正确性 15%
        ScoreDimension.CODE_ROBUSTNESS: 0.15,       # 健壮性 15%
        ScoreDimension.CODE_READABILITY: 0.20,      # 可读性 20%
        ScoreDimension.CODE_MAINTAINABILITY: 0.20,  # 可维护性 20%
        ScoreDimension.CODE_ARCHITECTURE: 0.15,     # 架构设计 15%
        ScoreDimension.CODE_PERFORMANCE: 0.08,      # 性能 8%
        ScoreDimension.CODE_SECURITY: 0.07          # 安全性 7%
    }
    
    def _get_category(self) -> str:
        return "code"
    
    async def evaluate(self, content: Union[str, Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        """评估代码质量"""
        start_time = time.time()
        
        # 解析代码内容
        code_analysis = await self._parse_code_content(content)
        if not code_analysis["files"]:
            raise ValueError("未找到有效的代码文件")
        
        # 分析代码
        analysis = await self._analyze_code(code_analysis)
        
        # 生成各维度评分
        breakdown = [
            await self._evaluate_correctness(analysis),
            await self._evaluate_robustness(analysis),
            await self._evaluate_readability(analysis),
            await self._evaluate_maintainability(analysis),
            await self._evaluate_architecture(analysis),
            await self._evaluate_performance(analysis),
            await self._evaluate_security(analysis)
        ]
        
        # 计算总分
        overall_score = self._calculate_score(breakdown)
        
        # 生成诊断
        diagnosis = self._generate_diagnosis(breakdown, analysis)
        
        # 收集证据
        evidence = self._collect_evidence(analysis)
        
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
    
    async def _parse_code_content(self, content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """解析代码内容"""
        files = {}
        repo_info = {}
        
        if isinstance(content, dict):
            # 处理包含仓库链接和代码片段的复合内容
            if "code_repo" in content:
                repo_info = await self._analyze_repository(content["code_repo"])
                files.update(repo_info.get("files", {}))
            
            if "code_snippets" in content:
                for i, snippet in enumerate(content["code_snippets"]):
                    files[f"snippet_{i}.py"] = snippet
        
        elif isinstance(content, str):
            # 单个代码片段或仓库链接
            if content.startswith(("http://", "https://")):
                repo_info = await self._analyze_repository(content)
                files.update(repo_info.get("files", {}))
            else:
                files["main.py"] = content
        
        return {
            "files": files,
            "repo_info": repo_info,
            "total_files": len(files),
            "total_lines": sum(len(code.split('\n')) for code in files.values())
        }
    
    async def _analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """分析GitHub仓库(简化版本)"""
        # 这里应该实现真正的Git仓库分析
        # 由于复杂性，这里只是一个简化的模拟
        parsed_url = urlparse(repo_url)
        
        return {
            "url": repo_url,
            "platform": parsed_url.netloc,
            "files": {
                # 模拟一些代码文件
                "app.py": "# 模拟的主应用文件\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef read_root():\n    return {'Hello': 'World'}",
                "models.py": "# 模拟的模型文件\nfrom pydantic import BaseModel\nclass User(BaseModel):\n    name: str\n    age: int",
                "utils.py": "# 工具函数\ndef helper_function(x):\n    return x * 2"
            },
            "has_tests": False,
            "has_readme": True,
            "has_requirements": True,
            "commit_count": 10,
            "contributors": 1
        }
    
    async def _analyze_code(self, code_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码质量"""
        analysis = {
            "files": code_analysis["files"],
            "repo_info": code_analysis.get("repo_info", {}),
            "total_files": code_analysis["total_files"],
            "total_lines": code_analysis["total_lines"]
        }
        
        # 分析每个文件
        file_analyses = {}
        for filename, code in code_analysis["files"].items():
            file_analysis = await self._analyze_single_file(filename, code)
            file_analyses[filename] = file_analysis
        
        analysis["file_analyses"] = file_analyses
        
        # 聚合统计
        analysis.update(self._aggregate_file_statistics(file_analyses))
        
        return analysis
    
    async def _analyze_single_file(self, filename: str, code: str) -> Dict[str, Any]:
        """分析单个代码文件"""
        analysis = {
            "filename": filename,
            "language": self._detect_language(filename),
            "lines": len(code.split('\n')),
            "chars": len(code),
            "is_python": filename.endswith('.py')
        }
        
        if analysis["is_python"]:
            # Python代码特殊分析
            analysis.update(await self._analyze_python_code(code))
        else:
            # 通用代码分析
            analysis.update(await self._analyze_generic_code(code))
        
        return analysis
    
    def _detect_language(self, filename: str) -> str:
        """检测编程语言"""
        extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php'
        }
        
        for ext, lang in extensions.items():
            if filename.endswith(ext):
                return lang
        
        return 'unknown'
    
    async def _analyze_python_code(self, code: str) -> Dict[str, Any]:
        """分析Python代码"""
        analysis = {}
        
        try:
            # AST分析
            tree = ast.parse(code)
            visitor = PythonCodeVisitor()
            visitor.visit(tree)
            
            analysis.update({
                "functions": visitor.functions,
                "classes": visitor.classes,
                "imports": visitor.imports,
                "complexity": visitor.complexity,
                "docstrings": visitor.docstrings,
                "has_main_guard": "__main__" in code,
                "syntax_valid": True
            })
            
        except SyntaxError as e:
            analysis.update({
                "syntax_valid": False,
                "syntax_error": str(e),
                "functions": 0,
                "classes": 0,
                "imports": [],
                "complexity": 10,  # 高复杂度惩罚
                "docstrings": 0
            })
        
        # 代码风格分析
        analysis.update(self._analyze_code_style(code))
        
        # 安全性分析
        analysis.update(self._analyze_security_issues(code))
        
        return analysis
    
    async def _analyze_generic_code(self, code: str) -> Dict[str, Any]:
        """分析通用代码"""
        lines = code.split('\n')
        
        # 基础统计
        non_empty_lines = [line for line in lines if line.strip()]
        comment_lines = [line for line in lines if line.strip().startswith(('/', '#', '//', '/*', '*'))]
        
        # 缩进分析
        indented_lines = [line for line in lines if line.startswith((' ', '\t'))]
        
        # 函数/方法检测(简单的正则匹配)
        function_patterns = [
            r'def\s+\w+',      # Python
            r'function\s+\w+', # JavaScript
            r'public\s+\w+.*\(', # Java
            r'fn\s+\w+'        # Rust
        ]
        
        functions = 0
        for pattern in function_patterns:
            functions += len(re.findall(pattern, code))
        
        return {
            "syntax_valid": True,  # 假设语法正确
            "functions": functions,
            "classes": len(re.findall(r'class\s+\w+', code)),
            "imports": len(re.findall(r'import\s+\w+', code)),
            "complexity": min(len(non_empty_lines) // 10, 10),  # 简化的复杂度
            "docstrings": len(re.findall(r'""".*?"""', code, re.DOTALL)),
            "comment_ratio": len(comment_lines) / len(non_empty_lines) if non_empty_lines else 0,
            "indentation_consistent": len(set(len(line) - len(line.lstrip()) for line in indented_lines if line.strip())) <= 2
        }
    
    def _analyze_code_style(self, code: str) -> Dict[str, Any]:
        """分析代码风格"""
        lines = code.split('\n')
        
        # 命名约定检查
        snake_case_vars = len(re.findall(r'[a-z][a-z0-9_]*\s*=', code))
        camel_case_vars = len(re.findall(r'[a-z][a-zA-Z0-9]*\s*=', code))
        
        # 行长度检查
        long_lines = [line for line in lines if len(line) > 120]
        
        # 空行使用
        empty_lines = [line for line in lines if not line.strip()]
        
        return {
            "naming_consistency": snake_case_vars > camel_case_vars,
            "long_lines": len(long_lines),
            "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
            "empty_line_ratio": len(empty_lines) / len(lines) if lines else 0,
            "follows_pep8": len(long_lines) == 0 and snake_case_vars > camel_case_vars
        }
    
    def _analyze_security_issues(self, code: str) -> Dict[str, Any]:
        """分析安全问题"""
        security_issues = []
        
        # 检查危险函数调用
        dangerous_patterns = [
            (r'eval\s*\(', 'eval函数可能导致代码注入'),
            (r'exec\s*\(', 'exec函数可能导致代码注入'),
            (r'shell=True', 'subprocess使用shell=True可能不安全'),
            (r'input\s*\(', '直接使用input可能不安全'),
            (r'pickle\.loads\s*\(', 'pickle.loads可能导致代码执行'),
            (r'subprocess\.call.*shell=True', '使用shell=True可能导致命令注入')
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                security_issues.append(message)
        
        # 检查硬编码密码/密钥
        if re.search(r'(password|key|secret)\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            security_issues.append('可能包含硬编码密码或密钥')
        
        return {
            "security_issues": security_issues,
            "security_score": max(0, 10 - len(security_issues) * 2)
        }
    
    def _aggregate_file_statistics(self, file_analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """聚合文件统计信息"""
        if not file_analyses:
            return {}
        
        total_functions = sum(analysis.get("functions", 0) for analysis in file_analyses.values())
        total_classes = sum(analysis.get("classes", 0) for analysis in file_analyses.values())
        total_imports = sum(len(analysis.get("imports", [])) for analysis in file_analyses.values())
        
        syntax_errors = sum(1 for analysis in file_analyses.values() if not analysis.get("syntax_valid", True))
        
        avg_complexity = sum(analysis.get("complexity", 0) for analysis in file_analyses.values()) / len(file_analyses)
        
        has_tests = any("test" in filename.lower() for filename in file_analyses.keys())
        
        return {
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_imports": total_imports,
            "syntax_errors": syntax_errors,
            "avg_complexity": avg_complexity,
            "has_tests": has_tests,
            "test_coverage_estimated": 0.8 if has_tests else 0.0,
            "all_security_issues": [issue for analysis in file_analyses.values() 
                                  for issue in analysis.get("security_issues", [])]
        }
    
    async def _evaluate_correctness(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估正确性"""
        base_score = 80
        
        # 语法错误扣分
        syntax_penalty = analysis.get("syntax_errors", 0) * 20
        
        # 导入完整性加分
        import_score = min(analysis.get("total_imports", 0) * 2, 10)
        
        # 有主函数保护加分
        main_guard_bonus = 5 if any(analysis.get("file_analyses", {}).get(f, {}).get("has_main_guard", False) 
                                   for f in analysis.get("file_analyses", {})) else 0
        
        total_score = max(0, min(base_score - syntax_penalty + import_score + main_guard_bonus, 100))
        
        issues = []
        suggestions = []
        
        if analysis.get("syntax_errors", 0) > 0:
            issues.append(f"存在{analysis['syntax_errors']}个语法错误")
            suggestions.append("修复语法错误，确保代码可以正常运行")
        
        if analysis.get("total_imports", 0) == 0 and analysis.get("total_files", 0) > 1:
            issues.append("缺少必要的模块导入")
            suggestions.append("添加必要的import语句")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_CORRECTNESS,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_CORRECTNESS],
            evidence=[f"语法错误: {analysis.get('syntax_errors', 0)}", f"导入数量: {analysis.get('total_imports', 0)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_robustness(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估健壮性"""
        base_score = 60
        
        # 测试覆盖率
        test_score = analysis.get("test_coverage_estimated", 0) * 40
        
        # 错误处理(简单检查try-except)
        error_handling_score = 0
        for file_analysis in analysis.get("file_analyses", {}).values():
            if "try" in file_analysis.get("filename", "") or "except" in str(file_analysis):
                error_handling_score += 10
                break
        
        total_score = min(base_score + test_score + error_handling_score, 100)
        
        issues = []
        suggestions = []
        
        if not analysis.get("has_tests", False):
            issues.append("缺少单元测试")
            suggestions.append("编写单元测试，目标覆盖率≥80%")
        
        if test_score < 20:
            issues.append("测试覆盖率不足")
            suggestions.append("增加测试用例，覆盖关键功能路径")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_ROBUSTNESS,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_ROBUSTNESS],
            evidence=[f"测试覆盖率: {analysis.get('test_coverage_estimated', 0):.0%}", f"包含测试: {analysis.get('has_tests', False)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_readability(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估可读性"""
        base_score = 70
        
        # 注释比例
        comment_ratios = [fa.get("comment_ratio", 0) for fa in analysis.get("file_analyses", {}).values()]
        avg_comment_ratio = sum(comment_ratios) / len(comment_ratios) if comment_ratios else 0
        comment_score = min(avg_comment_ratio * 100, 20) if avg_comment_ratio > 0.1 else -10
        
        # 命名规范
        naming_scores = [10 if fa.get("naming_consistency", False) else -5 
                        for fa in analysis.get("file_analyses", {}).values()]
        avg_naming_score = sum(naming_scores) / len(naming_scores) if naming_scores else 0
        
        # 文档字符串
        docstring_count = sum(fa.get("docstrings", 0) for fa in analysis.get("file_analyses", {}).values())
        docstring_score = min(docstring_count * 5, 15)
        
        total_score = min(base_score + comment_score + avg_naming_score + docstring_score, 100)
        
        issues = []
        suggestions = []
        
        if avg_comment_ratio < 0.1:
            issues.append("注释过少")
            suggestions.append("添加必要的注释，解释复杂逻辑")
        
        if docstring_count == 0:
            issues.append("缺少文档字符串")
            suggestions.append("为函数和类添加文档字符串")
        
        if avg_naming_score < 0:
            issues.append("命名规范不一致")
            suggestions.append("统一使用snake_case命名风格")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_READABILITY,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_READABILITY],
            evidence=[f"注释比例: {avg_comment_ratio:.1%}", f"文档字符串: {docstring_count}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_maintainability(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估可维护性"""
        base_score = 65
        
        # 复杂度
        avg_complexity = analysis.get("avg_complexity", 5)
        complexity_score = max(0, 20 - avg_complexity * 2)
        
        # 模块化程度
        modular_score = min(analysis.get("total_files", 1) * 5, 20) if analysis.get("total_files", 1) > 1 else -10
        
        # 函数平均长度(估算)
        avg_lines_per_function = (analysis.get("total_lines", 100) / 
                                 max(analysis.get("total_functions", 1), 1))
        function_size_score = 10 if avg_lines_per_function < 20 else -5
        
        total_score = min(base_score + complexity_score + modular_score + function_size_score, 100)
        
        issues = []
        suggestions = []
        
        if avg_complexity > 7:
            issues.append("代码复杂度过高")
            suggestions.append("拆分复杂函数，降低圈复杂度")
        
        if analysis.get("total_files", 1) == 1 and analysis.get("total_lines", 0) > 200:
            issues.append("单文件代码过长")
            suggestions.append("将代码拆分到多个模块")
        
        if avg_lines_per_function > 30:
            issues.append("函数过长")
            suggestions.append("拆分长函数，提高代码可读性")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_MAINTAINABILITY,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_MAINTAINABILITY],
            evidence=[f"平均复杂度: {avg_complexity:.1f}", f"文件数量: {analysis.get('total_files', 1)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_architecture(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估架构设计"""
        base_score = 60
        
        # 分层结构
        has_models = any("model" in f.lower() for f in analysis.get("file_analyses", {}))
        has_views = any("view" in f.lower() or "controller" in f.lower() or "api" in f.lower() 
                       for f in analysis.get("file_analyses", {}))
        has_utils = any("util" in f.lower() or "helper" in f.lower() 
                       for f in analysis.get("file_analyses", {}))
        
        architecture_score = (has_models + has_views + has_utils) * 10
        
        # 类的使用
        class_score = min(analysis.get("total_classes", 0) * 5, 20)
        
        # 接口设计(通过函数数量和模块化程度评估)
        interface_score = min(analysis.get("total_functions", 0), 10)
        
        total_score = min(base_score + architecture_score + class_score + interface_score, 100)
        
        issues = []
        suggestions = []
        
        if not (has_models or has_views or has_utils):
            issues.append("缺乏清晰的架构分层")
            suggestions.append("按照MVC或类似模式组织代码结构")
        
        if analysis.get("total_classes", 0) == 0 and analysis.get("total_functions", 0) > 10:
            issues.append("缺少面向对象设计")
            suggestions.append("考虑使用类来组织相关功能")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_ARCHITECTURE,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_ARCHITECTURE],
            evidence=[f"类数量: {analysis.get('total_classes', 0)}", f"函数数量: {analysis.get('total_functions', 0)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_performance(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估性能"""
        base_score = 75
        
        # 复杂度对性能的影响
        complexity_penalty = max(0, (analysis.get("avg_complexity", 5) - 5) * 3)
        
        # 文件大小合理性
        avg_lines_per_file = analysis.get("total_lines", 100) / max(analysis.get("total_files", 1), 1)
        size_score = 10 if avg_lines_per_file < 200 else -5
        
        total_score = max(0, min(base_score - complexity_penalty + size_score, 100))
        
        issues = []
        suggestions = []
        
        if analysis.get("avg_complexity", 5) > 8:
            issues.append("算法复杂度过高可能影响性能")
            suggestions.append("优化算法，降低时间复杂度")
        
        if avg_lines_per_file > 500:
            issues.append("文件过大可能影响加载性能")
            suggestions.append("拆分大文件，提高模块加载效率")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_PERFORMANCE,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_PERFORMANCE],
            evidence=[f"平均复杂度: {analysis.get('avg_complexity', 5):.1f}", f"平均文件大小: {avg_lines_per_file:.0f}行"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_security(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估安全性"""
        base_score = 80
        
        # 安全问题扣分
        security_issues = analysis.get("all_security_issues", [])
        security_penalty = len(security_issues) * 15
        
        total_score = max(0, min(base_score - security_penalty, 100))
        
        issues = []
        suggestions = []
        
        for issue in security_issues[:3]:  # 只显示前3个
            issues.append(issue)
            suggestions.append("审查并修复安全隐患")
        
        if not issues:
            # 没有明显安全问题时的建议
            if analysis.get("total_imports", 0) > 0:
                suggestions.append("继续保持良好的安全编码实践")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.CODE_SECURITY,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.CODE_SECURITY],
            evidence=[f"安全问题数量: {len(security_issues)}"],
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
    
    def _collect_evidence(self, analysis: Dict[str, Any]) -> List[str]:
        """收集评估证据"""
        evidence = [
            f"代码文件数量: {analysis.get('total_files', 0)}",
            f"代码总行数: {analysis.get('total_lines', 0)}",
            f"函数数量: {analysis.get('total_functions', 0)}",
            f"类数量: {analysis.get('total_classes', 0)}",
            f"平均复杂度: {analysis.get('avg_complexity', 0):.1f}",
            f"语法错误: {analysis.get('syntax_errors', 0)}",
            f"安全问题: {len(analysis.get('all_security_issues', []))}"
        ]
        
        if analysis.get("has_tests", False):
            evidence.append("✓ 包含测试文件")
        if analysis.get("syntax_errors", 0) == 0:
            evidence.append("✓ 语法正确")
        if len(analysis.get("all_security_issues", [])) == 0:
            evidence.append("✓ 无明显安全问题")
        
        return evidence


class PythonCodeVisitor(ast.NodeVisitor):
    """Python代码AST访问器"""
    
    def __init__(self):
        self.functions = 0
        self.classes = 0
        self.imports = []
        self.complexity = 0
        self.docstrings = 0
        
    def visit_FunctionDef(self, node):
        self.functions += 1
        # 计算函数复杂度(简化版本)
        self.complexity += 1 + len([n for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While))])
        
        # 检查文档字符串
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Str)):
            self.docstrings += 1
            
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)  # 异步函数按普通函数处理
        
    def visit_ClassDef(self, node):
        self.classes += 1
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Str)):
            self.docstrings += 1
        self.generic_visit(node)
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

