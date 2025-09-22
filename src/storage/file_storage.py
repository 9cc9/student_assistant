"""文件存储系统 - 防止评估记录因重启丢失"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FileStorage:
    """文件存储系统"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # 评估记录存储文件
        self.assessments_file = self.storage_dir / "assessments.json"
        self._load_assessments()
    
    def _load_assessments(self) -> None:
        """加载评估记录"""
        try:
            if self.assessments_file.exists():
                with open(self.assessments_file, 'r', encoding='utf-8') as f:
                    self._assessments = json.load(f)
                logger.info(f"📂 加载了 {len(self._assessments)} 条评估记录")
            else:
                self._assessments = {}
                logger.info("📂 初始化空的评估记录存储")
        except Exception as e:
            logger.error(f"📂 加载评估记录失败: {str(e)}")
            self._assessments = {}
    
    def _save_assessments(self) -> None:
        """保存评估记录"""
        try:
            # 转换datetime为字符串
            save_data = {}
            for assessment_id, assessment in self._assessments.items():
                save_data[assessment_id] = self._serialize_assessment(assessment)
            
            with open(self.assessments_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📂 保存了 {len(save_data)} 条评估记录")
        except Exception as e:
            logger.error(f"📂 保存评估记录失败: {str(e)}")
    
    def _serialize_assessment(self, assessment) -> Dict[str, Any]:
        """序列化评估记录"""
        try:
            if hasattr(assessment, '__dict__'):
                data = assessment.__dict__.copy()
            else:
                data = assessment
            
            # 处理datetime字段
            if 'created_at' in data and hasattr(data['created_at'], 'isoformat'):
                data['created_at'] = data['created_at'].isoformat()
            if 'updated_at' in data and data['updated_at'] and hasattr(data['updated_at'], 'isoformat'):
                data['updated_at'] = data['updated_at'].isoformat()
            if 'completed_at' in data and data['completed_at'] and hasattr(data['completed_at'], 'isoformat'):
                data['completed_at'] = data['completed_at'].isoformat()
            
            # 处理枚举字段
            if 'status' in data and hasattr(data['status'], 'value'):
                data['status'] = data['status'].value
            if 'assessment_level' in data and data['assessment_level'] and hasattr(data['assessment_level'], 'value'):
                data['assessment_level'] = data['assessment_level'].value
            
            # 处理嵌套对象
            if 'result' in data and data['result'] and hasattr(data['result'], '__dict__'):
                data['result'] = data['result'].__dict__.copy()
            
            if 'deliverables' in data and data['deliverables'] and hasattr(data['deliverables'], '__dict__'):
                data['deliverables'] = data['deliverables'].__dict__.copy()
            
            if 'score_breakdown' in data and data['score_breakdown'] and hasattr(data['score_breakdown'], '__dict__'):
                data['score_breakdown'] = data['score_breakdown'].__dict__.copy()
            
            if 'exit_rules' in data and data['exit_rules'] and hasattr(data['exit_rules'], '__dict__'):
                data['exit_rules'] = data['exit_rules'].__dict__.copy()
            
            # 处理列表中的对象
            if 'diagnosis' in data and data['diagnosis']:
                diagnosis_list = []
                for diag in data['diagnosis']:
                    if hasattr(diag, '__dict__'):
                        diagnosis_list.append(diag.__dict__.copy())
                    else:
                        diagnosis_list.append(diag)
                data['diagnosis'] = diagnosis_list
            
            return data
        except Exception as e:
            logger.error(f"📂 序列化评估记录失败: {str(e)}")
            return {"error": str(e)}
    
    def save_assessment(self, assessment_id: str, assessment: Any) -> None:
        """保存单个评估记录"""
        try:
            self._assessments[assessment_id] = assessment
            self._save_assessments()
            logger.info(f"📂 ✅ 保存评估记录: {assessment_id}")
        except Exception as e:
            logger.error(f"📂 ❌ 保存评估记录失败: {assessment_id}, {str(e)}")
    
    def get_assessment(self, assessment_id: str) -> Optional[Any]:
        """获取评估记录"""
        assessment_data = self._assessments.get(assessment_id)
        if assessment_data and isinstance(assessment_data, dict):
            # 将字典转换回Assessment对象
            return self._deserialize_assessment(assessment_data)
        return assessment_data
    
    def _deserialize_assessment(self, data: Dict[str, Any]) -> Any:
        """反序列化评估记录"""
        try:
            from ..models.assessment import Assessment, AssessmentStatus, AssessmentLevel, Deliverables
            from datetime import datetime
            
            # 处理datetime字段
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data and data['updated_at'] and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            if 'completed_at' in data and data['completed_at'] and isinstance(data['completed_at'], str):
                data['completed_at'] = datetime.fromisoformat(data['completed_at'])
            
            # 处理枚举字段
            if 'status' in data and isinstance(data['status'], str):
                data['status'] = AssessmentStatus(data['status'])
            if 'assessment_level' in data and data['assessment_level'] and isinstance(data['assessment_level'], str):
                data['assessment_level'] = AssessmentLevel(data['assessment_level'])
            
            # 处理Deliverables对象
            if 'deliverables' in data and isinstance(data['deliverables'], dict):
                deliverables_data = data['deliverables']
                data['deliverables'] = Deliverables(**deliverables_data)
            
            # 创建Assessment对象（只包含必需的字段）
            required_fields = ['assessment_id', 'student_id', 'deliverables', 'status', 'created_at']
            assessment_dict = {k: v for k, v in data.items() if k in required_fields}
            
            # 创建基本的Assessment对象
            assessment = Assessment(**assessment_dict)
            
            # 设置其他字段
            for key, value in data.items():
                if key not in required_fields and hasattr(assessment, key):
                    setattr(assessment, key, value)
            
            return assessment
            
        except Exception as e:
            logger.error(f"📂 反序列化评估记录失败: {str(e)}")
            return data  # 返回原始数据
    
    def list_assessments(self) -> Dict[str, Any]:
        """列出所有评估记录"""
        return self._assessments.copy()
    
    def delete_assessment(self, assessment_id: str) -> bool:
        """删除评估记录"""
        if assessment_id in self._assessments:
            del self._assessments[assessment_id]
            self._save_assessments()
            logger.info(f"📂 🗑️ 删除评估记录: {assessment_id}")
            return True
        return False


# 全局存储实例
_storage_instance = None

def get_storage() -> FileStorage:
    """获取存储实例（单例模式）"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = FileStorage()
    return _storage_instance
