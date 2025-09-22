"""学生相关数据模型"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class LearningLevel(Enum):
    """学习水平枚举"""
    L0 = "L0"  # 零基础
    L1 = "L1"  # 初级
    L2 = "L2"  # 中级
    L3 = "L3"  # 高级/竞赛型


class LearningStyle(Enum):
    """学习风格枚举"""
    EXAMPLES_FIRST = "examples_first"  # 示例优先
    THEORY_FIRST = "theory_first"      # 理论优先
    HANDS_ON = "hands_on"              # 动手实践
    VISUAL = "visual"                   # 视觉化学习


@dataclass
class StudentProfile:
    """学生学习画像"""
    student_id: str
    level: LearningLevel  # 水平分层（L0/L1/L2/L3）
    weak_skills: List[str]  # 薄弱技能
    interests: List[str]    # 兴趣方向
    learning_style: LearningStyle  # 学习风格
    time_budget_hours_per_week: int  # 每周学习时间预算
    goals: List[str]  # 学习目标
    
    # 历史学习数据
    mastery_scores: Dict[str, float] = None  # 各技能掌握度
    frustration_level: float = 0.0  # 挫败感水平（0-1）
    retry_count: int = 0  # 重试次数
    
    def __post_init__(self):
        if self.mastery_scores is None:
            self.mastery_scores = {}


@dataclass
class LearningNode:
    """学习节点"""
    node_id: str
    name: str
    description: str
    prerequisites: List[str]  # 前置节点
    estimated_hours: int  # 预计学习时间
    
    # 三档任务包
    channel_a_tasks: List[str]  # A档：基础保底任务
    channel_b_tasks: List[str]  # B档：标准实践任务
    channel_c_tasks: List[str]  # C档：挑战拓展任务


@dataclass
class Checkpoint:
    """门槛卡检查点"""
    checkpoint_id: str
    node_id: str  # 所属节点
    must_pass: List[str]  # 必须通过的条件
    evidence: List[str]   # 需要的证据
    auto_grade_rules: Dict[str, any]  # 自动评分规则
    
    # 门槛要求
    min_score: float = 60.0  # 最低通过分数
    max_retries: int = 3     # 最大重试次数


@dataclass
class LearningPath:
    """学习路径"""
    path_id: str
    student_id: str
    nodes: List[LearningNode]  # 学习节点序列
    current_node: str          # 当前节点
    current_channel: str       # 当前通道（A/B/C）
    
    # 进度跟踪
    completed_nodes: List[str] = None
    node_channels: Dict[str, str] = None  # 各节点使用的通道
    
    def __post_init__(self):
        if self.completed_nodes is None:
            self.completed_nodes = []
        if self.node_channels is None:
            self.node_channels = {}


@dataclass 
class Student:
    """学生实体"""
    student_id: str
    name: str
    email: str
    profile: StudentProfile
    current_path: Optional[LearningPath] = None
    
    # 学习记录
    assessment_history: List[str] = None  # 评估历史ID列表
    created_at: str = None
    
    def __post_init__(self):
        if self.assessment_history is None:
            self.assessment_history = []