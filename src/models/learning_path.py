"""学习路径相关数据模型"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Channel(str, Enum):
    """学习通道"""
    A = "A"  # 基础保底
    B = "B"  # 标准实践
    C = "C"  # 挑战拓展


class NodeStatus(str, Enum):
    """节点状态"""
    LOCKED = "locked"       # 锁定
    AVAILABLE = "available" # 可用
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed" # 完成
    FAILED = "failed"       # 失败


class PathDecision(str, Enum):
    """路径决策"""
    UPGRADE = "upgrade"     # 升级通道
    KEEP = "keep"          # 保持当前通道
    DOWNGRADE = "downgrade_with_scaffold"  # 降级并提供脚手架


class CheckpointRule(BaseModel):
    """门槛卡规则"""
    checkpoint_id: str = Field(..., description="门槛卡ID")
    must_pass: List[str] = Field(..., description="必须通过的要求")
    evidence: List[str] = Field(..., description="需要的证据")
    auto_grade: Dict[str, Any] = Field(default_factory=dict, description="自动评分标准")
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkpoint_id": "RAG-01",
                "must_pass": ["能独立构建索引", "能解释召回与精排差异"],
                "evidence": ["仓库链接", "短视频讲解", "在线演示"],
                "auto_grade": {
                    "unit_test_coverage": 0.9,
                    "latency_ms_at_k5": 800
                }
            }
        }


class PathNode(BaseModel):
    """路径节点"""
    id: str = Field(..., description="节点ID")
    name: str = Field(..., description="节点名称")
    description: str = Field(..., description="节点描述")
    order: int = Field(..., description="顺序")
    
    # 通道任务
    channel_tasks: Dict[Channel, Dict[str, Any]] = Field(..., description="各通道任务")
    
    # 前置依赖
    prerequisites: List[str] = Field(default_factory=list, description="前置节点ID")
    
    # 门槛卡
    checkpoint: Optional[CheckpointRule] = Field(None, description="门槛卡规则")
    
    # 补救资源
    remedy_resources: Dict[str, List[str]] = Field(default_factory=dict, description="补救资源")
    
    # 元数据
    estimated_hours: Dict[Channel, int] = Field(default_factory=dict, description="预估学习时长")
    difficulty_level: Dict[Channel, int] = Field(default_factory=dict, description="难度等级(1-10)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "api_calling",
                "name": "API调用",
                "description": "学习如何调用各种API接口",
                "order": 1,
                "channel_tasks": {
                    "A": {"task": "用SDK完成3个API调用", "requirements": ["调用成功", "处理错误"]},
                    "B": {"task": "手写HTTP并处理鉴权/限流", "requirements": ["实现鉴权", "错误处理", "限流控制"]},
                    "C": {"task": "封装可复用SDK并发布包", "requirements": ["SDK设计", "单元测试", "文档完善", "发布到PyPI"]}
                },
                "estimated_hours": {"A": 4, "B": 8, "C": 16},
                "difficulty_level": {"A": 3, "B": 6, "C": 9}
            }
        }


class StudentPathProgress(BaseModel):
    """学生路径进度"""
    student_id: str = Field(..., description="学生ID")
    current_node_id: str = Field(..., description="当前节点ID")
    current_channel: Channel = Field(..., description="当前通道")
    node_statuses: Dict[str, NodeStatus] = Field(default_factory=dict, description="节点状态")
    completed_nodes: List[str] = Field(default_factory=list, description="已完成节点")
    
    # 学习统计
    total_study_hours: float = Field(default=0, description="总学习时长")
    mastery_scores: Dict[str, float] = Field(default_factory=dict, description="掌握度分数")
    frustration_level: float = Field(default=0, description="挫折度(0-1)")
    retry_counts: Dict[str, int] = Field(default_factory=dict, description="重试次数")
    
    # 时间戳
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    last_activity_at: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class PathRecommendation(BaseModel):
    """路径推荐"""
    student_id: str = Field(..., description="学生ID")
    recommended_channel: Channel = Field(..., description="推荐通道")
    next_node_id: str = Field(..., description="下一个节点ID")
    decision: PathDecision = Field(..., description="决策类型")
    
    # 推荐理由
    reasoning: str = Field(..., description="推荐理由")
    trigger_factors: Dict[str, Any] = Field(default_factory=dict, description="触发因子")
    alternative_options: List[Dict[str, Any]] = Field(default_factory=list, description="备选方案")
    
    # 补救建议
    scaffold_resources: List[str] = Field(default_factory=list, description="脚手架资源")
    estimated_completion_time: int = Field(..., description="预估完成时间(小时)")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class LearningPath(BaseModel):
    """学习路径"""
    id: str = Field(..., description="路径ID")
    name: str = Field(..., description="路径名称")
    description: str = Field(..., description="路径描述")
    nodes: List[PathNode] = Field(..., description="路径节点")
    
    # 路径配置
    default_channel: Channel = Field(default=Channel.B, description="默认通道")
    upgrade_threshold: float = Field(default=0.85, description="升级阈值")
    downgrade_threshold: float = Field(default=0.60, description="降级阈值")
    max_retries: int = Field(default=3, description="最大重试次数")
    
    # 元数据
    target_audience: List[str] = Field(default_factory=list, description="目标受众")
    prerequisites_knowledge: List[str] = Field(default_factory=list, description="前置知识")
    learning_outcomes: List[str] = Field(default_factory=list, description="学习成果")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

