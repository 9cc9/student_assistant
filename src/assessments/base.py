"""评估器基类"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..models import ScoreBreakdown, Diagnosis


class EvaluationResult(BaseModel):
    """评估结果基类"""
    category: str  # idea, ui, code
    overall_score: float  # 0-100
    breakdown: List[ScoreBreakdown]
    diagnosis: List[Diagnosis] 
    evidence: List[str]
    processing_time: float
    created_at: datetime


class BaseEvaluator(ABC):
    """评估器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.category = self._get_category()
        
    @abstractmethod
    def _get_category(self) -> str:
        """获取评估类别"""
        pass
    
    @abstractmethod
    async def evaluate(self, content: Any, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        """
        评估内容
        
        Args:
            content: 待评估内容
            context: 评估上下文信息
            
        Returns:
            EvaluationResult: 评估结果
        """
        pass
    
    @abstractmethod
    def _calculate_score(self, breakdown: List[ScoreBreakdown]) -> float:
        """计算总分"""
        pass
    
    def _validate_input(self, content: Any) -> bool:
        """验证输入内容"""
        return content is not None
    
    def _generate_suggestions(self, diagnosis: List[Diagnosis]) -> List[str]:
        """根据诊断结果生成建议"""
        suggestions = []
        for item in diagnosis:
            if item.priority == 1:
                suggestions.append(f"紧急修复: {item.fix}")
            elif item.priority <= 3: 
                suggestions.append(f"重要改进: {item.fix}")
            else:
                suggestions.append(f"建议优化: {item.fix}")
        return suggestions

