"""数据库模型定义"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, BigInteger, Text, 
    DateTime, Boolean, Enum, JSON, ForeignKey, Index
)
from sqlalchemy.types import DECIMAL as Decimal
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT

Base = declarative_base()


class Student(Base):
    """学生基础信息表"""
    __tablename__ = 'students'
    
    student_id = Column(String(50), primary_key=True, comment='学生ID')
    name = Column(String(100), nullable=False, comment='学生姓名')
    email = Column(String(100), nullable=False, unique=True, comment='邮箱')
    phone = Column(String(20), comment='手机号')
    password_hash = Column(String(255), comment='密码哈希')
    level = Column(Enum('L0', 'L1', 'L2', 'L3'), nullable=False, default='L0', comment='学习水平')
    learning_style = Column(Enum('examples_first', 'theory_first', 'hands_on', 'visual'), 
                          nullable=False, default='examples_first', comment='学习风格')
    time_budget_hours_per_week = Column(Integer, nullable=False, default=6, comment='每周学习时间预算(小时)')
    weak_skills = Column(JSON, comment='薄弱技能列表')
    interests = Column(JSON, comment='兴趣方向列表')
    goals = Column(JSON, comment='学习目标列表')
    mastery_scores = Column(JSON, comment='各技能掌握度分数')
    frustration_level = Column(Decimal(3, 2), nullable=False, default=0.00, comment='挫败感水平(0-1)')
    retry_count = Column(Integer, nullable=False, default=0, comment='总重试次数')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    progress = relationship("StudentProgress", back_populates="student", uselist=False, cascade="all, delete-orphan")
    progress_nodes = relationship("StudentProgressNode", back_populates="student", cascade="all, delete-orphan")
    diagnostics = relationship("Diagnostic", back_populates="student", cascade="all, delete-orphan")
    assessment_runs = relationship("AssessmentRun", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Student(student_id='{self.student_id}', name='{self.name}', level='{self.level}')>"


class StudentProgress(Base):
    """学生全局进度表"""
    __tablename__ = 'student_progress'
    
    student_id = Column(String(50), ForeignKey('students.student_id', ondelete='CASCADE'), 
                       primary_key=True, comment='学生ID')
    current_node_id = Column(String(100), nullable=False, comment='当前节点ID')
    current_channel = Column(Enum('A', 'B', 'C'), nullable=False, default='B', comment='当前通道')
    total_study_hours = Column(Decimal(8, 2), nullable=False, default=0.00, comment='总学习时长(小时)')
    frustration_level = Column(Decimal(3, 2), nullable=False, default=0.00, comment='当前挫败感水平(0-1)')
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='开始学习时间')
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='最后活动时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    student = relationship("Student", back_populates="progress")
    
    def __repr__(self):
        return f"<StudentProgress(student_id='{self.student_id}', current_node='{self.current_node_id}', channel='{self.current_channel}')>"


class StudentProgressNode(Base):
    """学生节点进度详情表"""
    __tablename__ = 'student_progress_nodes'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    student_id = Column(String(50), ForeignKey('students.student_id', ondelete='CASCADE'), 
                       nullable=False, comment='学生ID')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    status = Column(Enum('locked', 'available', 'in_progress', 'completed', 'failed'), 
                   nullable=False, default='locked', comment='节点状态')
    used_channel = Column(Enum('A', 'B', 'C'), comment='使用的通道')
    score = Column(Decimal(5, 2), comment='节点得分(0-100)')
    attempt_count = Column(Integer, nullable=False, default=0, comment='尝试次数')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    student = relationship("Student", back_populates="progress_nodes")
    
    # 唯一约束
    __table_args__ = (
        Index('uk_student_node', 'student_id', 'node_id', unique=True),
    )
    
    def __repr__(self):
        return f"<StudentProgressNode(student_id='{self.student_id}', node_id='{self.node_id}', status='{self.status}')>"


class Diagnostic(Base):
    """诊断记录表"""
    __tablename__ = 'diagnostics'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    student_id = Column(String(50), ForeignKey('students.student_id', ondelete='CASCADE'), 
                       nullable=False, comment='学生ID')
    diagnostic_id = Column(String(100), nullable=False, unique=True, comment='诊断ID')
    diagnostic_type = Column(String(50), nullable=False, comment='诊断类型')
    overall_score = Column(Decimal(5, 2), nullable=False, comment='总体得分(0-100)')
    concept_score = Column(Decimal(5, 2), comment='概念理解得分')
    coding_score = Column(Decimal(5, 2), comment='编程能力得分')
    tool_familiarity = Column(Decimal(5, 2), comment='工具熟悉度得分')
    skill_scores = Column(JSON, comment='各技能详细得分')
    learning_style_preference = Column(String(50), comment='学习风格偏好')
    time_budget_hours_per_week = Column(Integer, comment='每周学习时间预算')
    goals = Column(JSON, comment='学习目标')
    interests = Column(JSON, comment='兴趣方向')
    recommendations = Column(JSON, comment='推荐建议')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    
    # 关系
    student = relationship("Student", back_populates="diagnostics")
    items = relationship("DiagnosticItem", back_populates="diagnostic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Diagnostic(diagnostic_id='{self.diagnostic_id}', student_id='{self.student_id}', score={self.overall_score})>"


class DiagnosticItem(Base):
    """诊断题目明细表"""
    __tablename__ = 'diagnostic_items'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    diagnostic_id = Column(String(100), ForeignKey('diagnostics.diagnostic_id', ondelete='CASCADE'), 
                          nullable=False, comment='诊断ID')
    item_id = Column(String(100), nullable=False, comment='题目ID')
    item_type = Column(String(50), nullable=False, comment='题目类型')
    question = Column(Text, nullable=False, comment='题目内容')
    answer = Column(Text, comment='学生答案')
    correct_answer = Column(Text, comment='正确答案')
    score = Column(Decimal(5, 2), comment='得分')
    max_score = Column(Decimal(5, 2), nullable=False, default=100.00, comment='满分')
    dimension = Column(String(100), comment='评价维度')
    difficulty_level = Column(Integer, comment='难度等级(1-10)')
    time_spent_seconds = Column(Integer, comment='答题用时(秒)')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    
    # 关系
    diagnostic = relationship("Diagnostic", back_populates="items")
    
    def __repr__(self):
        return f"<DiagnosticItem(item_id='{self.item_id}', diagnostic_id='{self.diagnostic_id}', score={self.score})>"


class Assessment(Base):
    """评分规则表"""
    __tablename__ = 'assessments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    assessment_id = Column(String(100), nullable=False, unique=True, comment='评分规则ID')
    name = Column(String(200), nullable=False, comment='评分规则名称')
    description = Column(Text, comment='评分规则描述')
    assessment_type = Column(String(50), nullable=False, comment='评分类型')
    node_id = Column(String(100), comment='关联节点ID')
    channel = Column(Enum('A', 'B', 'C'), comment='适用通道')
    rubric = Column(JSON, nullable=False, comment='评分细则')
    weight_idea = Column(Decimal(3, 2), nullable=False, default=0.30, comment='Idea权重')
    weight_ui = Column(Decimal(3, 2), nullable=False, default=0.30, comment='UI权重')
    weight_code = Column(Decimal(3, 2), nullable=False, default=0.40, comment='Code权重')
    pass_threshold = Column(Decimal(5, 2), nullable=False, default=60.00, comment='通过阈值')
    excellent_threshold = Column(Decimal(5, 2), nullable=False, default=85.00, comment='优秀阈值')
    max_retries = Column(Integer, nullable=False, default=3, comment='最大重试次数')
    is_active = Column(Boolean, nullable=False, default=True, comment='是否启用')
    version = Column(String(20), nullable=False, default='1.0', comment='版本号')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    runs = relationship("AssessmentRun", back_populates="assessment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Assessment(assessment_id='{self.assessment_id}', name='{self.name}', type='{self.assessment_type}')>"


class AssessmentRun(Base):
    """评分执行记录表"""
    __tablename__ = 'assessment_runs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    run_id = Column(String(100), nullable=False, unique=True, comment='评分执行ID')
    student_id = Column(String(50), ForeignKey('students.student_id', ondelete='CASCADE'), 
                       nullable=False, comment='学生ID')
    assessment_id = Column(String(100), ForeignKey('assessments.assessment_id', ondelete='RESTRICT'), 
                          nullable=False, comment='评分规则ID')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    channel = Column(Enum('A', 'B', 'C'), nullable=False, comment='使用通道')
    status = Column(Enum('queued', 'in_progress', 'completed', 'failed'), 
                   nullable=False, default='queued', comment='执行状态')
    overall_score = Column(Decimal(5, 2), comment='总体得分')
    idea_score = Column(Decimal(5, 2), comment='Idea得分')
    ui_score = Column(Decimal(5, 2), comment='UI得分')
    code_score = Column(Decimal(5, 2), comment='Code得分')
    detailed_scores = Column(JSON, comment='详细评分')
    assessment_level = Column(Enum('pass', 'excellent', 'need_improvement'), comment='评估等级')
    diagnosis = Column(JSON, comment='诊断信息')
    resources = Column(JSON, comment='推荐资源')
    exit_rules = Column(JSON, comment='准出规则')
    error_message = Column(Text, comment='错误信息')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    student = relationship("Student", back_populates="assessment_runs")
    assessment = relationship("Assessment", back_populates="runs")
    submissions = relationship("Submission", back_populates="assessment_run")
    
    def __repr__(self):
        return f"<AssessmentRun(run_id='{self.run_id}', student_id='{self.student_id}', status='{self.status}')>"


class Submission(Base):
    """提交记录表"""
    __tablename__ = 'submissions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    submission_id = Column(String(100), nullable=False, unique=True, comment='提交ID')
    student_id = Column(String(50), ForeignKey('students.student_id', ondelete='CASCADE'), 
                       nullable=False, comment='学生ID')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    channel = Column(Enum('A', 'B', 'C'), nullable=False, comment='使用通道')
    assessment_run_id = Column(String(100), ForeignKey('assessment_runs.run_id', ondelete='SET NULL'), 
                              comment='关联评分执行ID')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_type = Column(String(50), nullable=False, comment='文件类型')
    file_size = Column(BigInteger, comment='文件大小(字节)')
    content_hash = Column(String(64), comment='内容哈希')
    idea_text = Column(Text, comment='Idea文本')
    ui_images = Column(JSON, comment='UI图片列表')
    code_snippets = Column(JSON, comment='代码片段')
    code_repo = Column(String(500), comment='代码仓库链接')
    submission_type = Column(String(50), nullable=False, default='code', comment='提交类型')
    status = Column(Enum('pending', 'processing', 'completed', 'failed'), 
                   nullable=False, default='pending', comment='处理状态')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    student = relationship("Student", back_populates="submissions")
    assessment_run = relationship("AssessmentRun", back_populates="submissions")
    
    def __repr__(self):
        return f"<Submission(submission_id='{self.submission_id}', student_id='{self.student_id}', type='{self.submission_type}')>"
