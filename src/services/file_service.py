"""文件处理服务"""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import subprocess
import git
from git.exc import GitCommandError

logger = logging.getLogger(__name__)


class FileService:
    """文件和代码仓库处理服务"""
    
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = Path(upload_dir).resolve()
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # 如果无法在当前目录创建，使用临时目录
            import tempfile
            self.upload_dir = Path(tempfile.gettempdir()) / "ai_assistant_uploads"
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的文件类型
        self.supported_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.html', '.css', '.scss', '.less', '.vue', '.md', '.txt', '.json',
            '.yaml', '.yml', '.xml', '.sql', '.sh', '.bat', '.dockerfile'
        }
        
        # 排除的目录和文件
        self.exclude_patterns = {
            'node_modules', '__pycache__', '.git', '.svn', '.idea', '.vscode',
            'dist', 'build', 'target', 'bin', 'obj', '.DS_Store', 'Thumbs.db',
            '*.log', '*.tmp', '*.cache'
        }
    
    async def process_uploaded_files(self, files: List[Any], student_id: str) -> Dict[str, Any]:
        """
        处理上传的文件
        
        Args:
            files: 上传的文件列表
            student_id: 学生ID
            
        Returns:
            处理结果
        """
        try:
            # 创建学生专用目录
            student_dir = self.upload_dir / student_id / datetime.now().strftime("%Y%m%d_%H%M%S")
            student_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_files = []
            
            for file in files:
                file_path = student_dir / file.filename
                
                # 保存上传的文件
                content = await file.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # 如果是压缩文件，解压缩
                if file.filename.lower().endswith(('.zip', '.tar.gz', '.tar')):
                    extracted_files.extend(await self._extract_archive(file_path, student_dir))
                else:
                    extracted_files.append(file_path)
            
            # 分析提取的文件
            analysis_result = await self._analyze_project_structure(student_dir)
            
            logger.info(f"文件处理完成，学生: {student_id}, 文件数: {len(extracted_files)}")
            
            return {
                "student_id": student_id,
                "upload_path": str(student_dir),
                "files_count": len(extracted_files),
                "analysis": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            raise FileProcessingError(f"文件处理失败: {str(e)}")
    
    async def clone_git_repository(self, repo_url: str, student_id: str, 
                                 branch: str = "main") -> Dict[str, Any]:
        """
        克隆Git仓库
        
        Args:
            repo_url: Git仓库URL
            student_id: 学生ID
            branch: 分支名称
            
        Returns:
            克隆结果
        """
        try:
            # 创建克隆目录
            clone_dir = self.upload_dir / student_id / f"git_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            clone_dir.mkdir(parents=True, exist_ok=True)
            
            # 克隆仓库
            logger.info(f"开始克隆仓库: {repo_url}")
            repo = git.Repo.clone_from(repo_url, clone_dir)
            
            # 切换到指定分支
            if branch != "main" and branch in [ref.name.split('/')[-1] for ref in repo.refs]:
                repo.git.checkout(branch)
            
            # 分析项目结构
            analysis_result = await self._analyze_project_structure(clone_dir)
            
            # 获取仓库信息
            repo_info = {
                "url": repo_url,
                "branch": branch,
                "last_commit": str(repo.head.commit),
                "last_commit_message": repo.head.commit.message.strip(),
                "last_commit_date": repo.head.commit.committed_datetime.isoformat(),
                "total_commits": len(list(repo.iter_commits()))
            }
            
            logger.info(f"Git仓库克隆完成: {repo_url}")
            
            return {
                "student_id": student_id,
                "repo_path": str(clone_dir),
                "repo_info": repo_info,
                "analysis": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except GitCommandError as e:
            logger.error(f"Git克隆失败: {str(e)}")
            raise GitProcessingError(f"Git仓库克隆失败: {str(e)}")
        except Exception as e:
            logger.error(f"仓库处理失败: {str(e)}")
            raise FileProcessingError(f"仓库处理失败: {str(e)}")
    
    async def _extract_archive(self, archive_path: Path, extract_dir: Path) -> List[Path]:
        """提取压缩文件"""
        extracted_files = []
        
        try:
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    extracted_files = [extract_dir / name for name in zip_ref.namelist() 
                                     if not name.endswith('/')]
            else:
                # 支持tar.gz等其他格式
                subprocess.run(['tar', '-xf', str(archive_path), '-C', str(extract_dir)], 
                             check=True, capture_output=True)
                extracted_files = list(extract_dir.rglob('*'))
                
        except Exception as e:
            logger.warning(f"压缩文件提取失败: {str(e)}")
            
        return extracted_files
    
    async def _analyze_project_structure(self, project_dir: Path) -> Dict[str, Any]:
        """
        分析项目结构
        
        Args:
            project_dir: 项目目录
            
        Returns:
            分析结果
        """
        try:
            analysis = {
                "total_files": 0,
                "code_files": 0,
                "languages": {},
                "frameworks": [],
                "file_tree": [],
                "main_files": [],
                "config_files": [],
                "documentation": [],
                "tests": [],
                "lines_of_code": 0
            }
            
            # 遍历项目文件
            for file_path in project_dir.rglob('*'):
                if file_path.is_file() and not self._should_exclude(file_path):
                    analysis["total_files"] += 1
                    
                    # 分析文件类型
                    if file_path.suffix.lower() in self.supported_extensions:
                        analysis["code_files"] += 1
                        
                        # 统计编程语言
                        lang = self._detect_language(file_path)
                        if lang:
                            analysis["languages"][lang] = analysis["languages"].get(lang, 0) + 1
                        
                        # 统计代码行数
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = len(f.readlines())
                                analysis["lines_of_code"] += lines
                        except:
                            pass
                    
                    # 识别特殊文件
                    filename = file_path.name.lower()
                    if filename in ['main.py', 'app.py', 'index.js', 'main.js', 'index.html']:
                        analysis["main_files"].append(str(file_path.relative_to(project_dir)))
                    elif filename in ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle', 'Cargo.toml']:
                        analysis["config_files"].append(str(file_path.relative_to(project_dir)))
                    elif filename in ['readme.md', 'readme.txt', 'docs']:
                        analysis["documentation"].append(str(file_path.relative_to(project_dir)))
                    elif 'test' in filename or filename.endswith('_test.py'):
                        analysis["tests"].append(str(file_path.relative_to(project_dir)))
            
            # 检测框架
            analysis["frameworks"] = await self._detect_frameworks(project_dir)
            
            # 生成文件树（限制深度）
            analysis["file_tree"] = self._generate_file_tree(project_dir, max_depth=3)
            
            return analysis
            
        except Exception as e:
            logger.error(f"项目结构分析失败: {str(e)}")
            return {"error": str(e)}
    
    def _should_exclude(self, file_path: Path) -> bool:
        """检查文件是否应该被排除"""
        path_parts = file_path.parts
        for part in path_parts:
            if part in self.exclude_patterns:
                return True
        return False
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """检测文件编程语言"""
        suffix = file_path.suffix.lower()
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React JSX',
            '.tsx': 'React TSX',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.vue': 'Vue.js'
        }
        return language_map.get(suffix)
    
    async def _detect_frameworks(self, project_dir: Path) -> List[str]:
        """检测使用的框架"""
        frameworks = []
        
        # 检查package.json
        package_json = project_dir / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    
                    if 'react' in deps:
                        frameworks.append('React')
                    if 'vue' in deps:
                        frameworks.append('Vue.js')
                    if 'angular' in deps:
                        frameworks.append('Angular')
                    if 'express' in deps:
                        frameworks.append('Express.js')
                    if 'next' in deps:
                        frameworks.append('Next.js')
            except:
                pass
        
        # 检查requirements.txt
        requirements = project_dir / "requirements.txt"
        if requirements.exists():
            try:
                with open(requirements, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if 'django' in content:
                        frameworks.append('Django')
                    if 'flask' in content:
                        frameworks.append('Flask')
                    if 'fastapi' in content:
                        frameworks.append('FastAPI')
                    if 'streamlit' in content:
                        frameworks.append('Streamlit')
            except:
                pass
        
        # 检查特定文件
        if (project_dir / "manage.py").exists():
            frameworks.append('Django')
        if (project_dir / "app.py").exists() or (project_dir / "main.py").exists():
            if not any(f in frameworks for f in ['Django', 'FastAPI']):
                frameworks.append('Python Web App')
        
        return frameworks
    
    def _generate_file_tree(self, directory: Path, max_depth: int = 3, current_depth: int = 0) -> List[Dict]:
        """生成文件树结构"""
        if current_depth >= max_depth:
            return []
        
        tree = []
        try:
            for item in sorted(directory.iterdir()):
                if self._should_exclude(item):
                    continue
                
                node = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item.relative_to(directory.parent))
                }
                
                if item.is_dir() and current_depth < max_depth - 1:
                    node["children"] = self._generate_file_tree(item, max_depth, current_depth + 1)
                
                tree.append(node)
        except PermissionError:
            pass
        
        return tree
    
    def get_project_summary(self, project_path: str) -> Dict[str, Any]:
        """获取项目摘要信息，用于评估"""
        project_dir = Path(project_path)
        
        summary = {
            "main_language": None,
            "frameworks": [],
            "total_files": 0,
            "lines_of_code": 0,
            "has_tests": False,
            "has_documentation": False,
            "key_files": [],
            "code_samples": {}
        }
        
        if not project_dir.exists():
            return summary
        
        # 分析代码文件
        code_files = []
        for file_path in project_dir.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix.lower() in self.supported_extensions and
                not self._should_exclude(file_path)):
                code_files.append(file_path)
        
        # 统计语言使用情况
        language_count = {}
        for file_path in code_files:
            lang = self._detect_language(file_path)
            if lang:
                language_count[lang] = language_count.get(lang, 0) + 1
        
        if language_count:
            summary["main_language"] = max(language_count, key=language_count.get)
        
        summary["total_files"] = len(code_files)
        
        # 获取代码示例
        for file_path in code_files[:5]:  # 最多取5个文件作为示例
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if len(content.strip()) > 0:
                        summary["code_samples"][str(file_path.relative_to(project_dir))] = content[:2000]  # 限制长度
            except:
                pass
        
        return summary


class FileProcessingError(Exception):
    """文件处理错误"""
    pass


class GitProcessingError(Exception):
    """Git处理错误"""
    pass
