"""提交物相关数据模型"""
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SubmissionType(Enum):
    """提交类型枚举"""
    INITIAL = "initial"      # 初次提交
    RESUBMISSION = "resubmission"  # 二次提交


class SubmissionStatus(Enum):
    """提交状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    REJECTED = "rejected"      # 被拒绝


@dataclass
class CodeRepository:
    """代码仓库信息"""
    repo_url: str
    branch: str = "main"
    commit_hash: Optional[str] = None
    language: Optional[str] = None  # 主要编程语言
    framework: Optional[str] = None  # 使用的框架
    
    # 代码统计信息
    lines_of_code: int = 0
    test_coverage: float = 0.0  # 测试覆盖率
    files_count: int = 0


@dataclass
class UIDesign:
    """UI设计信息"""
    design_images: List[str]  # 设计图片（base64或URL）
    prototype_url: Optional[str] = None  # 原型链接
    design_tool: Optional[str] = None  # 设计工具（Figma、Sketch等）
    
    # UI规范信息
    design_system: Optional[str] = None  # 设计系统（Material、HIG等）
    color_palette: List[str] = None      # 色彩方案
    typography: Dict = None              # 字体排版信息
    
    def __post_init__(self):
        if self.color_palette is None:
            self.color_palette = []
        if self.typography is None:
            self.typography = {}


@dataclass
class IdeaDescription:
    """创意描述信息"""
    title: str
    description: str
    target_users: str           # 目标用户
    core_features: List[str]    # 核心功能
    
    # 可行性分析
    technical_stack: List[str] = None   # 技术栈
    estimated_timeline: Optional[str] = None  # 预计时间线
    resource_requirements: List[str] = None   # 资源需求
    potential_challenges: List[str] = None    # 潜在挑战
    
    def __post_init__(self):
        if self.technical_stack is None:
            self.technical_stack = []
        if self.resource_requirements is None:
            self.resource_requirements = []
        if self.potential_challenges is None:
            self.potential_challenges = []


@dataclass
class Submission:
    """提交物主实体"""
    submission_id: str
    student_id: str
    node_id: str  # 所属学习节点
    channel: str  # 通道（A/B/C）
    submission_type: SubmissionType
    status: SubmissionStatus  # 状态信息
    created_at: datetime
    
    # 提交内容
    idea: IdeaDescription
    ui_design: UIDesign
    code_repo: CodeRepository
    
    # 可选字段（有默认值的放在后面）
    code_snippets: List[str] = None
    updated_at: Optional[datetime] = None
    assessment_id: Optional[str] = None
    notes: Optional[str] = None  # 学生备注
    attachments: List[str] = None  # 附件列表
    
    def __post_init__(self):
        if self.code_snippets is None:
            self.code_snippets = []
        if self.attachments is None:
            self.attachments = []
    
    def update_status(self, new_status: SubmissionStatus, notes: Optional[str] = None):
        """更新提交状态"""
        self.status = new_status
        self.updated_at = datetime.now()
        if notes:
            self.notes = notes


@dataclass
class ComparisonResult:
    """对比结果（用于二次提交对比）"""
    original_submission_id: str
    new_submission_id: str
    comparison_date: datetime
    
    # 各维度改进情况
    idea_improvement: float     # Idea改进分数
    ui_improvement: float       # UI改进分数
    code_improvement: float     # 代码改进分数
    overall_improvement: float  # 综合改进分数
    
    # 具体改进点
    improvements: List[str] = None      # 改进点列表
    remaining_issues: List[str] = None  # 仍需改进的问题
    
    def __post_init__(self):
        if self.improvements is None:
            self.improvements = []
        if self.remaining_issues is None:
            self.remaining_issues = []