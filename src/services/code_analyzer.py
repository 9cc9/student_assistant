"""增强的代码分析服务"""
import ast
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import logging
from dataclasses import dataclass
import subprocess
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class CodeMetrics:
    """代码指标"""
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    complexity: int = 0
    functions_count: int = 0
    classes_count: int = 0
    imports_count: int = 0
    test_coverage: float = 0.0


@dataclass
class CodeIssue:
    """代码问题"""
    file_path: str
    line_number: int
    issue_type: str  # style, logic, security, performance
    severity: str    # low, medium, high, critical
    message: str
    suggestion: str


class EnhancedCodeAnalyzer:
    """增强的代码分析器"""
    
    def __init__(self):
        self.supported_languages = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby'
        }
    
    async def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """
        分析整个项目
        
        Args:
            project_path: 项目路径
            
        Returns:
            分析结果
        """
        try:
            project_dir = Path(project_path)
            
            if not project_dir.exists():
                raise ValueError(f"项目路径不存在: {project_path}")
            
            analysis_result = {
                "project_path": project_path,
                "overall_metrics": CodeMetrics(),
                "file_analyses": {},
                "issues": [],
                "recommendations": [],
                "architecture_analysis": {},
                "security_analysis": {},
                "performance_analysis": {},
                "best_practices": {},
                "test_analysis": {}
            }
            
            # 获取所有代码文件
            code_files = self._get_code_files(project_dir)
            
            # 分析每个文件
            for file_path in code_files:
                file_analysis = await self._analyze_single_file(file_path)
                relative_path = str(file_path.relative_to(project_dir))
                analysis_result["file_analyses"][relative_path] = file_analysis
                
                # 累加指标
                self._accumulate_metrics(analysis_result["overall_metrics"], file_analysis["metrics"])
                
                # 收集问题
                analysis_result["issues"].extend(file_analysis.get("issues", []))
            
            # 项目级别分析
            analysis_result["architecture_analysis"] = await self._analyze_architecture(project_dir, code_files)
            analysis_result["security_analysis"] = await self._analyze_security(code_files)
            analysis_result["performance_analysis"] = await self._analyze_performance(code_files)
            analysis_result["best_practices"] = await self._check_best_practices(project_dir, code_files)
            analysis_result["test_analysis"] = await self._analyze_tests(project_dir)
            
            # 生成建议
            analysis_result["recommendations"] = self._generate_recommendations(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"项目分析失败: {str(e)}")
            raise CodeAnalysisError(f"项目分析失败: {str(e)}")
    
    def _get_code_files(self, project_dir: Path) -> List[Path]:
        """获取所有代码文件"""
        code_files = []
        exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build'}
        
        for file_path in project_dir.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix in self.supported_languages and
                not any(part in exclude_dirs for part in file_path.parts)):
                code_files.append(file_path)
        
        return code_files
    
    async def _analyze_single_file(self, file_path: Path) -> Dict[str, Any]:
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            language = self.supported_languages.get(file_path.suffix, 'unknown')
            
            analysis = {
                "file_path": str(file_path),
                "language": language,
                "size_bytes": len(content.encode('utf-8')),
                "metrics": self._calculate_basic_metrics(content),
                "issues": [],
                "quality_score": 0.0
            }
            
            # 根据语言进行特定分析
            if language == 'python':
                python_analysis = await self._analyze_python_file(file_path, content)
                analysis.update(python_analysis)
            elif language in ['javascript', 'typescript']:
                js_analysis = await self._analyze_javascript_file(file_path, content)
                analysis.update(js_analysis)
            
            # 计算质量评分
            analysis["quality_score"] = self._calculate_quality_score(analysis)
            
            return analysis
            
        except Exception as e:
            logger.warning(f"文件分析失败: {file_path}, 错误: {str(e)}")
            return {
                "file_path": str(file_path),
                "error": str(e),
                "metrics": CodeMetrics(),
                "issues": [],
                "quality_score": 0.0
            }
    
    def _calculate_basic_metrics(self, content: str) -> CodeMetrics:
        """计算基本代码指标"""
        lines = content.split('\n')
        
        metrics = CodeMetrics()
        metrics.lines_of_code = len([line for line in lines if line.strip()])
        metrics.blank_lines = len([line for line in lines if not line.strip()])
        
        # 简单的注释检测
        comment_patterns = [r'^\s*#', r'^\s*//', r'^\s*/\*', r'^\s*\*']
        for line in lines:
            if any(re.match(pattern, line) for pattern in comment_patterns):
                metrics.comment_lines += 1
        
        return metrics
    
    async def _analyze_python_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """分析Python文件"""
        analysis = {
            "ast_analysis": {},
            "issues": [],
            "suggestions": []
        }
        
        try:
            tree = ast.parse(content)
            visitor = PythonASTVisitor()
            visitor.visit(tree)
            
            analysis["ast_analysis"] = {
                "functions": visitor.functions,
                "classes": visitor.classes,
                "imports": visitor.imports,
                "complexity": visitor.complexity
            }
            
            # 代码风格检查
            style_issues = self._check_python_style(content)
            analysis["issues"].extend(style_issues)
            
            # 安全性检查
            security_issues = self._check_python_security(content)
            analysis["issues"].extend(security_issues)
            
        except SyntaxError as e:
            analysis["issues"].append(CodeIssue(
                file_path=str(file_path),
                line_number=e.lineno or 1,
                issue_type="syntax",
                severity="critical",
                message=f"语法错误: {e.msg}",
                suggestion="修复语法错误"
            ))
        except Exception as e:
            logger.warning(f"Python分析失败: {str(e)}")
        
        return analysis
    
    async def _analyze_javascript_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """分析JavaScript/TypeScript文件"""
        analysis = {
            "issues": [],
            "suggestions": []
        }
        
        # JavaScript特定检查
        js_issues = self._check_javascript_patterns(content, str(file_path))
        analysis["issues"].extend(js_issues)
        
        return analysis
    
    def _check_python_style(self, content: str) -> List[CodeIssue]:
        """检查Python代码风格"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 检查行长度
            if len(line) > 120:
                issues.append(CodeIssue(
                    file_path="",
                    line_number=i,
                    issue_type="style",
                    severity="low",
                    message=f"行过长 ({len(line)} 字符)",
                    suggestion="考虑将长行拆分为多行"
                ))
            
            # 检查缩进
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                continue
            elif '\t' in line and ' ' * 4 in line:
                issues.append(CodeIssue(
                    file_path="",
                    line_number=i,
                    issue_type="style", 
                    severity="medium",
                    message="混合使用了空格和制表符缩进",
                    suggestion="统一使用4个空格进行缩进"
                ))
        
        return issues
    
    def _check_python_security(self, content: str) -> List[CodeIssue]:
        """检查Python安全性问题"""
        issues = []
        
        # 检查危险函数使用
        dangerous_patterns = [
            (r'eval\s*\(', "使用eval()函数可能存在代码注入风险"),
            (r'exec\s*\(', "使用exec()函数可能存在代码注入风险"),
            (r'os\.system\s*\(', "使用os.system()可能存在命令注入风险"),
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "subprocess使用shell=True可能存在安全风险")
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in dangerous_patterns:
                if re.search(pattern, line):
                    issues.append(CodeIssue(
                        file_path="",
                        line_number=i,
                        issue_type="security",
                        severity="high",
                        message=message,
                        suggestion="考虑使用更安全的替代方案"
                    ))
        
        return issues
    
    def _check_javascript_patterns(self, content: str, file_path: str) -> List[CodeIssue]:
        """检查JavaScript代码模式"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 检查console.log (在生产环境中应该移除)
            if 'console.log' in line and 'TODO' not in line and 'DEBUG' not in line:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    issue_type="style",
                    severity="low", 
                    message="包含console.log语句",
                    suggestion="在生产环境中移除调试输出"
                ))
            
            # 检查var使用 (推荐使用let/const)
            if re.search(r'\bvar\s+', line):
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    issue_type="style",
                    severity="medium",
                    message="使用了var声明变量",
                    suggestion="推荐使用let或const声明变量"
                ))
        
        return issues
    
    async def _analyze_architecture(self, project_dir: Path, code_files: List[Path]) -> Dict[str, Any]:
        """分析项目架构"""
        architecture = {
            "structure_score": 0.0,
            "modularity_score": 0.0,
            "coupling_analysis": {},
            "patterns": [],
            "suggestions": []
        }
        
        # 目录结构分析
        depth_score = self._analyze_directory_structure(project_dir)
        architecture["structure_score"] = depth_score
        
        # 模块化分析
        modularity = self._analyze_modularity(code_files)
        architecture["modularity_score"] = modularity
        
        # 设计模式检测
        patterns = self._detect_design_patterns(code_files)
        architecture["patterns"] = patterns
        
        return architecture
    
    async def _analyze_security(self, code_files: List[Path]) -> Dict[str, Any]:
        """安全性分析"""
        security = {
            "vulnerability_count": 0,
            "security_score": 100.0,
            "issues": [],
            "recommendations": []
        }
        
        # 这里可以集成更多安全检查工具
        return security
    
    async def _analyze_performance(self, code_files: List[Path]) -> Dict[str, Any]:
        """性能分析"""
        performance = {
            "performance_score": 0.0,
            "bottlenecks": [],
            "optimization_suggestions": []
        }
        
        # 性能相关模式检查
        return performance
    
    async def _check_best_practices(self, project_dir: Path, code_files: List[Path]) -> Dict[str, Any]:
        """检查最佳实践"""
        best_practices = {
            "score": 0.0,
            "checklist": {
                "has_readme": (project_dir / "README.md").exists(),
                "has_gitignore": (project_dir / ".gitignore").exists(),
                "has_requirements": (project_dir / "requirements.txt").exists() or (project_dir / "package.json").exists(),
                "has_tests": self._has_test_files(project_dir),
                "has_docs": self._has_documentation(project_dir)
            },
            "suggestions": []
        }
        
        # 计算最佳实践评分
        score = sum(best_practices["checklist"].values()) / len(best_practices["checklist"]) * 100
        best_practices["score"] = score
        
        # 生成建议
        if not best_practices["checklist"]["has_readme"]:
            best_practices["suggestions"].append("添加README.md文件说明项目")
        if not best_practices["checklist"]["has_tests"]:
            best_practices["suggestions"].append("添加测试文件提高代码质量")
        
        return best_practices
    
    async def _analyze_tests(self, project_dir: Path) -> Dict[str, Any]:
        """测试分析"""
        test_analysis = {
            "has_tests": False,
            "test_files_count": 0,
            "test_coverage_estimate": 0.0,
            "test_frameworks": []
        }
        
        # 查找测试文件
        test_patterns = ['test_*.py', '*_test.py', 'test*.js', '*.test.js', '*.spec.js']
        test_files = []
        
        for pattern in test_patterns:
            test_files.extend(project_dir.rglob(pattern))
        
        test_analysis["test_files_count"] = len(test_files)
        test_analysis["has_tests"] = len(test_files) > 0
        
        # 简单的测试覆盖率估算
        if test_files:
            total_test_lines = 0
            for test_file in test_files:
                try:
                    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                        total_test_lines += len([line for line in f.readlines() if line.strip()])
                except:
                    pass
            
            # 简单估算：测试行数 / (代码行数 * 0.3) * 100
            if total_test_lines > 0:
                test_analysis["test_coverage_estimate"] = min(100, (total_test_lines / 100) * 30)
        
        return test_analysis
    
    def _analyze_directory_structure(self, project_dir: Path) -> float:
        """分析目录结构合理性"""
        depth_score = 100.0
        max_depth = 0
        
        for item in project_dir.rglob('*'):
            if item.is_file():
                depth = len(item.parts) - len(project_dir.parts)
                max_depth = max(max_depth, depth)
        
        # 目录过深扣分
        if max_depth > 6:
            depth_score -= (max_depth - 6) * 10
        
        return max(0, depth_score)
    
    def _analyze_modularity(self, code_files: List[Path]) -> float:
        """分析模块化程度"""
        if len(code_files) <= 1:
            return 50.0  # 单文件项目模块化程度一般
        
        # 基于文件数量和组织结构给出模块化评分
        file_count = len(code_files)
        if file_count > 20:
            return 90.0
        elif file_count > 10:
            return 80.0
        elif file_count > 5:
            return 70.0
        else:
            return 60.0
    
    def _detect_design_patterns(self, code_files: List[Path]) -> List[str]:
        """检测设计模式"""
        patterns = []
        
        # 简单的模式检测逻辑
        for file_path in code_files:
            filename = file_path.name.lower()
            if 'factory' in filename:
                patterns.append('Factory Pattern')
            if 'singleton' in filename:
                patterns.append('Singleton Pattern')
            if 'observer' in filename:
                patterns.append('Observer Pattern')
        
        return list(set(patterns))
    
    def _has_test_files(self, project_dir: Path) -> bool:
        """检查是否有测试文件"""
        test_patterns = ['test_*.py', '*_test.py', '*.test.js', '*.spec.js']
        for pattern in test_patterns:
            if list(project_dir.rglob(pattern)):
                return True
        return False
    
    def _has_documentation(self, project_dir: Path) -> bool:
        """检查是否有文档"""
        doc_files = ['docs', 'doc', 'README.md', 'README.txt']
        for doc in doc_files:
            if (project_dir / doc).exists():
                return True
        return False
    
    def _accumulate_metrics(self, overall: CodeMetrics, file_metrics: CodeMetrics):
        """累加指标"""
        overall.lines_of_code += file_metrics.lines_of_code
        overall.blank_lines += file_metrics.blank_lines
        overall.comment_lines += file_metrics.comment_lines
        overall.complexity += file_metrics.complexity
        overall.functions_count += file_metrics.functions_count
        overall.classes_count += file_metrics.classes_count
        overall.imports_count += file_metrics.imports_count
    
    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> float:
        """计算质量评分"""
        score = 100.0
        
        # 根据问题严重程度扣分
        for issue in analysis.get("issues", []):
            if issue.severity == "critical":
                score -= 20
            elif issue.severity == "high":
                score -= 10
            elif issue.severity == "medium":
                score -= 5
            elif issue.severity == "low":
                score -= 2
        
        return max(0, score)
    
    def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于分析结果生成建议
        overall_metrics = analysis_result["overall_metrics"]
        
        # 代码规模建议
        if overall_metrics.lines_of_code > 10000:
            recommendations.append("项目规模较大，建议考虑拆分为多个模块")
        
        # 注释率建议
        comment_ratio = overall_metrics.comment_lines / max(overall_metrics.lines_of_code, 1)
        if comment_ratio < 0.1:
            recommendations.append("代码注释较少，建议增加注释提高可读性")
        
        # 测试建议
        test_analysis = analysis_result.get("test_analysis", {})
        if not test_analysis.get("has_tests", False):
            recommendations.append("缺少测试文件，建议添加单元测试提高代码质量")
        
        # 架构建议
        architecture = analysis_result.get("architecture_analysis", {})
        if architecture.get("structure_score", 100) < 70:
            recommendations.append("目录结构过于复杂，建议重新组织项目结构")
        
        return recommendations


class PythonASTVisitor(ast.NodeVisitor):
    """Python AST 访问器"""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
        self.complexity = 0
    
    def visit_FunctionDef(self, node):
        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "args_count": len(node.args.args)
        })
        # 计算复杂度（简化版本）
        self.complexity += 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                self.complexity += 1
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "methods": []
        })
        self.generic_visit(node)
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)


class CodeAnalysisError(Exception):
    """代码分析错误"""
    pass
