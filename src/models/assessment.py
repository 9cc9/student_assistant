"""评估相关数据模型"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class AssessmentStatus(Enum):
    """评估状态枚举"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AssessmentLevel(Enum):
    """评估等级枚举"""
    PASS = "pass"  # 通过 >= 60
    EXCELLENT = "excellent"  # 优秀 >= 85
    NEED_IMPROVEMENT = "need_improvement"  # 需改进 < 60


@dataclass
class Deliverables:
    """提交物数据模型"""
    idea_text: str  # Idea文本描述
    ui_images: List[str]  # UI设计图（base64编码）
    code_repo: Optional[str] = None  # 代码仓库链接
    code_snippets: List[str] = None  # 代码片段
    
    def __post_init__(self):
        if self.code_snippets is None:
            self.code_snippets = []


@dataclass
class ScoreBreakdown:
    """评分详细信息"""
    idea: float  # Idea评分（30%）
    ui: float    # UI评分（30%）
    code: float  # Code评分（40%）
    
    @property
    def overall_score(self) -> float:
        """计算综合评分"""
        return self.idea * 0.3 + self.ui * 0.3 + self.code * 0.4


@dataclass
class Diagnosis:
    """诊断信息"""
    dimension: str  # 评价维度，如"ui.accessibility"
    issue: str      # 问题描述
    fix: str        # 修复建议
    priority: int = 1  # 优先级（1-5，1最高）


@dataclass
class ExitRule:
    """准出规则"""
    pass_status: bool  # 是否通过
    path_update: Dict  # 路径更新信息
    remedy: List[str]  # 补救措施


@dataclass
class Assessment:
    """评估记录模型"""
    assessment_id: str
    student_id: str
    deliverables: Deliverables
    status: AssessmentStatus
    created_at: datetime
    
    # 评估结果
    score_breakdown: Optional[ScoreBreakdown] = None
    detailed_scores: Optional['DetailedScores'] = None  # 详细的子维度评分
    overall_score: Optional[float] = None
    assessment_level: Optional[AssessmentLevel] = None
    diagnosis: List[Diagnosis] = None
    resources: List[str] = None  # 推荐学习资源
    exit_rules: Optional[ExitRule] = None
    
    # 元数据
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.diagnosis is None:
            self.diagnosis = []
        if self.resources is None:
            self.resources = []
    
    def mark_completed(self, score_breakdown: ScoreBreakdown, 
                      diagnosis: List[Diagnosis], resources: List[str],
                      exit_rules: ExitRule):
        """标记评估完成"""
        self.status = AssessmentStatus.COMPLETED
        self.score_breakdown = score_breakdown
        self.overall_score = score_breakdown.overall_score
        self.diagnosis = diagnosis
        self.resources = resources
        self.exit_rules = exit_rules
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 确定评估等级
        if self.overall_score >= 85:
            self.assessment_level = AssessmentLevel.EXCELLENT
        elif self.overall_score >= 60:
            self.assessment_level = AssessmentLevel.PASS
        else:
            self.assessment_level = AssessmentLevel.NEED_IMPROVEMENT


@dataclass
class IdeaScore:
    """Idea评分详情"""
    innovation: float    # 创新性（新颖度/前沿性）
    feasibility: float   # 可行性（技术难度/周期/资源）
    learning_value: float # 学习价值（技能提升/知识拓展）
    
    @property
    def overall(self) -> float:
        """计算Idea总分"""
        return (self.innovation + self.feasibility + self.learning_value) / 3


@dataclass
class UIScore:
    """UI评分详情"""
    compliance: float        # 规范性（平台规范/HIG/Material）
    usability: float         # 可用性与可访问性（对比度/触达/可读性）
    information_arch: float  # 信息架构与视觉层次（布局/层级/一致性）
    
    @property
    def overall(self) -> float:
        """计算UI总分"""
        return (self.compliance + self.usability + self.information_arch) / 3


@dataclass
class CodeScore:
    """代码评分详情"""
    correctness: float      # 正确性与健壮性（单测覆盖/错误处理）
    readability: float      # 可读性与可维护性（命名/结构/注释）
    architecture: float     # 架构与最佳实践（模块化/模式/接口设计）
    performance: float      # 性能与安全（复杂度/资源占用/安全检查）
    
    @property
    def overall(self) -> float:
        """计算代码总分"""
        return (self.correctness + self.readability + self.architecture + self.performance) / 4


@dataclass
class DetailedScores:
    """详细评分信息"""
    idea: IdeaScore
    ui: UIScore
    code: CodeScore