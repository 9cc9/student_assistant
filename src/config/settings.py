"""系统配置设置"""
from typing import Dict, List
from dataclasses import dataclass
import os


@dataclass
class AIConfig:
    """AI服务配置"""
    # 阿里云通义千问配置
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "sk-6267c004c2ac41d69c098628660f41d0")
    qwen_model: str = "qwen-plus"  # 可选: qwen-max, qwen-plus, qwen-turbo
    qwen_base_url: str = "https://dashscope.aliyuncs.com/api/v1/"
    
    # 本地大模型配置
    local_model_url: str = "http://localhost:11434"  # Ollama默认地址
    local_model_name: str = "qwen2.5:14b"
    
    # 向量检索配置
    embedding_model: str = "text-embedding-v2"  # 阿里云文本向量化模型
    vector_dim: int = 1536
    similarity_threshold: float = 0.7


@dataclass
class DatabaseConfig:
    """数据库配置"""
    # 关系数据库配置（SQLite用于开发）
    database_url: str = "sqlite:///./student_assistant.db"
    
    # 向量数据库配置（FAISS）
    vector_db_path: str = "./data/vector_db"
    vector_index_path: str = "./data/vector_db/index.faiss"
    
    # Neo4j知识图谱配置
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")


@dataclass
class AssessmentConfig:
    """评估配置"""
    # 评分权重
    IDEA_WEIGHT: float = 0.3
    UI_WEIGHT: float = 0.3
    CODE_WEIGHT: float = 0.4
    
    # 评分门槛
    PASS_THRESHOLD: float = 60.0
    EXCELLENT_THRESHOLD: float = 85.0
    
    # 最大重试次数
    MAX_RETRIES: int = 3
    
    # 超时设置（秒）
    ASSESSMENT_TIMEOUT: int = 300
    
    # 各维度详细权重
    idea_weights: Dict[str, float] = None
    ui_weights: Dict[str, float] = None
    code_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.idea_weights is None:
            self.idea_weights = {
                "innovation": 0.4,      # 创新性
                "feasibility": 0.4,     # 可行性
                "learning_value": 0.2   # 学习价值
            }
        
        if self.ui_weights is None:
            self.ui_weights = {
                "compliance": 0.3,          # 规范性
                "usability": 0.4,           # 可用性与可访问性
                "information_arch": 0.3     # 信息架构与视觉层次
            }
        
        if self.code_weights is None:
            self.code_weights = {
                "correctness": 0.3,     # 正确性与健壮性
                "readability": 0.3,     # 可读性与可维护性
                "architecture": 0.2,    # 架构与最佳实践
                "performance": 0.2      # 性能与安全
            }


@dataclass
class PathConfig:
    """学习路径配置"""
    # 功能开关
    enable_path_integration: bool = False  # 是否启用学习路径集成功能
    
    # 通道难度系数
    CHANNEL_DIFFICULTY: Dict[str, float] = None
    
    # 掌握度决策规则参数
    MASTERY_UPGRADE_THRESHOLD: float = 0.85
    MASTERY_DOWNGRADE_THRESHOLD: float = 0.60
    FRUSTRATION_THRESHOLD: float = 0.2
    MAX_RETRIES_BEFORE_DOWNGRADE: int = 3
    
    # 补救路径配置
    SCAFFOLD_TYPES: List[str] = None
    
    def __post_init__(self):
        if self.CHANNEL_DIFFICULTY is None:
            self.CHANNEL_DIFFICULTY = {
                "A": 1.0,  # 基础保底
                "B": 1.2,  # 标准实践
                "C": 1.5   # 挑战拓展
            }
        
        if self.SCAFFOLD_TYPES is None:
            self.SCAFFOLD_TYPES = [
                "micro_course",     # 微课
                "guided_exercise",  # 引导题
                "example_case"      # 对照示例
            ]


@dataclass
class SystemConfig:
    """系统整体配置"""
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "./logs/student_assistant.log"
    
    # 缓存配置
    cache_expire_seconds: int = 3600
    
    # 文件存储配置
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    
    # 安全配置
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    jwt_expire_hours: int = 24
    
    # 性能配置
    max_workers: int = 4
    request_timeout_seconds: int = 30


# 全局配置实例
ai_config = AIConfig()
db_config = DatabaseConfig()
assessment_config = AssessmentConfig()
path_config = PathConfig()
system_config = SystemConfig()


def get_prompts() -> Dict[str, str]:
    """获取评估提示词模板"""
    return {
        "idea_evaluator": """
请评估以下学生项目创意，从三个维度进行评分（0-100分）：

1. 创新性（新颖度/前沿性）：
   - 创意是否具有新颖性和独特性
   - 是否涉及前沿技术或创新应用
   
2. 可行性（技术难度/周期/资源）：
   - 技术实现的可行性
   - 开发周期是否合理
   - 所需资源是否现实
   
3. 学习价值（技能提升/知识拓展）：
   - 对学生技能提升的帮助程度
   - 知识领域的拓展价值

学生创意：{idea_text}
技术栈：{technical_stack}
目标用户：{target_users}
核心功能：{core_features}

请返回JSON格式：
{
  "innovation": 分数,
  "feasibility": 分数,
  "learning_value": 分数,
  "feedback": "详细反馈",
  "suggestions": ["改进建议1", "改进建议2"]
}
""",

        "ui_evaluator": """
请评估以下UI设计，从三个维度进行评分（0-100分）：

1. 规范性（平台规范/HIG/Material）：
   - 是否遵循设计规范和指南
   - 设计一致性

2. 可用性与可访问性（对比度/触达/可读性）：
   - 界面可用性
   - 可访问性设计
   - 对比度和可读性

3. 信息架构与视觉层次（布局/层级/一致性）：
   - 信息组织是否合理
   - 视觉层次是否清晰
   - 布局是否美观

设计工具：{design_tool}
设计系统：{design_system}
色彩方案：{color_palette}

请返回JSON格式：
{
  "compliance": 分数,
  "usability": 分数,
  "information_arch": 分数,
  "feedback": "详细反馈",
  "suggestions": ["改进建议1", "改进建议2"]
}
""",

        "code_evaluator": """
请评估以下代码，从四个维度进行评分（0-100分）：

1. 正确性与健壮性（单测覆盖/错误处理）：
   - 代码逻辑正确性
   - 错误处理机制
   - 测试覆盖率

2. 可读性与可维护性（命名/结构/注释）：
   - 变量和函数命名
   - 代码结构清晰度
   - 注释完善程度

3. 架构与最佳实践（模块化/模式/接口设计）：
   - 代码模块化程度
   - 设计模式使用
   - 接口设计合理性

4. 性能与安全（复杂度/资源占用/安全检查）：
   - 算法复杂度
   - 资源使用效率
   - 安全性考虑

代码仓库：{repo_url}
主要语言：{language}
使用框架：{framework}
代码行数：{lines_of_code}
测试覆盖率：{test_coverage}%

请返回JSON格式：
{
  "correctness": 分数,
  "readability": 分数,
  "architecture": 分数,
  "performance": 分数,
  "feedback": "详细反馈",
  "suggestions": ["改进建议1", "改进建议2"],
  "issues": ["具体问题1", "具体问题2"]
}
"""
    }


# 准出规则模板
def get_exit_rules() -> Dict[str, Dict]:
    """获取准出规则配置"""
    return {
        "code_correctness": {
            "condition": "code.correctness < 70",
            "action": "require_additional_tests",
            "message": "要求补交单测≥80%覆盖；完成前不得进入'部署与监控'节点",
            "block_nodes": ["deployment", "monitoring"]
        },
        "ui_accessibility": {
            "condition": "ui.usability < 60", 
            "action": "require_accessibility_fixes",
            "message": "必须修复对比度、触控目标≥44pt；方可通过'UI评审'门槛",
            "requirements": ["contrast_ratio >= 4.5", "touch_target >= 44pt"]
        },
        "idea_feasibility": {
            "condition": "idea.feasibility < 65",
            "action": "require_feasibility_doc",
            "message": "需补交技术可行性分析文档并通过审核",
            "deliverables": ["feasibility_analysis.md"]
        }
    }