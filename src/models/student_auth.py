"""学生认证相关数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class StudentStatus(Enum):
    """学生账号状态"""
    ACTIVE = "active"       # 活跃
    INACTIVE = "inactive"   # 未激活
    SUSPENDED = "suspended" # 暂停


@dataclass
class StudentAccount:
    """
    学生账号模型
    
    Attributes:
        student_id: 学生ID（唯一标识）
        name: 学生姓名
        password_hash: 密码哈希值
        email: 邮箱（可选）
        status: 账号状态
        created_at: 创建时间
        last_login: 最后登录时间
    """
    student_id: str
    name: str
    password_hash: str
    email: Optional[str] = None
    status: StudentStatus = StudentStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
    
    def to_safe_dict(self) -> dict:
        """转换为安全字典（不包含密码）"""
        data = self.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StudentAccount':
        """从字典创建实例"""
        return cls(
            student_id=data["student_id"],
            name=data["name"],
            password_hash=data["password_hash"],
            email=data.get("email"),
            status=StudentStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_login=datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None
        )


@dataclass
class LoginSession:
    """
    登录会话模型
    
    Attributes:
        student_id: 学生ID
        token: JWT Token
        created_at: 创建时间
        expires_at: 过期时间
        ip_address: IP地址
    """
    student_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "student_id": self.student_id,
            "token": self.token,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ip_address": self.ip_address
        }


@dataclass
class DiagnosticRecord:
    """
    诊断记录模型
    
    Attributes:
        student_id: 学生ID
        test_id: 测试ID
        submitted_at: 提交时间
        concept_score: 概念理解分数
        coding_score: 编程能力分数
        tool_familiarity: 工具熟悉度
        overall_readiness: 整体准备度
        learning_level: 学习水平
        learning_style: 学习风格
        interests: 兴趣领域
    """
    student_id: str
    test_id: str
    submitted_at: datetime
    concept_score: int
    coding_score: int
    tool_familiarity: int
    overall_readiness: str
    learning_level: str = "B"
    learning_style: str = "hands_on"
    interests: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "student_id": self.student_id,
            "test_id": self.test_id,
            "submitted_at": self.submitted_at.isoformat(),
            "concept_score": self.concept_score,
            "coding_score": self.coding_score,
            "tool_familiarity": self.tool_familiarity,
            "overall_readiness": self.overall_readiness,
            "learning_level": self.learning_level,
            "learning_style": self.learning_style,
            "interests": self.interests
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DiagnosticRecord':
        """从字典创建实例"""
        return cls(
            student_id=data["student_id"],
            test_id=data["test_id"],
            submitted_at=datetime.fromisoformat(data["submitted_at"]),
            concept_score=data["concept_score"],
            coding_score=data["coding_score"],
            tool_familiarity=data["tool_familiarity"],
            overall_readiness=data["overall_readiness"],
            learning_level=data.get("learning_level", "B"),
            learning_style=data.get("learning_style", "hands_on"),
            interests=data.get("interests", [])
        )
