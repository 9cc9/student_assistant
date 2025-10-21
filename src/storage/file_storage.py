"""文件存储系统 - 防止评估记录因重启丢失"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from ..services.db_service import AssessmentDBService

logger = logging.getLogger(__name__)


class FileStorage:
    """文件存储系统"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # 评估记录存储文件（保留作为备份）
        self.assessments_file = self.storage_dir / "assessments.json"
        self._load_assessments()
        
        # 数据库服务
        self.assessment_db = AssessmentDBService()
    
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
                try:
                    serialized = self._serialize_assessment(assessment)
                    # 验证序列化后的数据可以转为JSON
                    json.dumps(serialized)  # 测试序列化
                    save_data[assessment_id] = serialized
                except Exception as e:
                    logger.error(f"📂 序列化评估记录失败: {assessment_id}, {str(e)}")
                    # 跳过有问题的记录，不影响其他记录
                    continue
            
            # 验证整个数据结构可以转为JSON
            json_str = json.dumps(save_data, ensure_ascii=False, indent=2)
            
            # 原子写入：先写入临时文件，再重命名
            temp_file = self.assessments_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
                f.flush()  # 确保数据写入磁盘
                os.fsync(f.fileno())  # 强制同步到磁盘
            
            # 原子重命名
            temp_file.replace(self.assessments_file)
            
            logger.info(f"📂 保存了 {len(save_data)} 条评估记录")
        except Exception as e:
            logger.error(f"📂 保存评估记录失败: {str(e)}")
            # 如果有临时文件，清理它
            temp_file = self.assessments_file.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
    
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
            
            # 处理详细评分字段
            if 'detailed_scores' in data and data['detailed_scores']:
                if hasattr(data['detailed_scores'], '__dict__'):
                    detailed_scores = data['detailed_scores'].__dict__.copy()
                    # 递归处理详细评分中的嵌套对象
                    for key, value in detailed_scores.items():
                        if value and hasattr(value, '__dict__'):
                            detailed_scores[key] = value.__dict__.copy()
                    data['detailed_scores'] = detailed_scores
                elif isinstance(data['detailed_scores'], dict):
                    # 如果已经是字典，检查是否有嵌套对象需要序列化
                    detailed_scores = data['detailed_scores'].copy()
                    for key, value in detailed_scores.items():
                        if value and hasattr(value, '__dict__'):
                            detailed_scores[key] = value.__dict__.copy()
                    data['detailed_scores'] = detailed_scores
                else:
                    # 如果是其他类型，设置为None
                    data['detailed_scores'] = None
            
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
            # 保存到数据库
            if hasattr(assessment, '__dict__'):
                assessment_data = assessment.__dict__.copy()
            else:
                assessment_data = assessment
            
            # 安全获取score_breakdown
            score_breakdown = assessment_data.get('score_breakdown')
            if score_breakdown is None:
                score_breakdown = {}
            elif hasattr(score_breakdown, '__dict__'):
                score_breakdown = score_breakdown.__dict__
            
            # 安全获取status
            status = assessment_data.get('status')
            if hasattr(status, 'value'):
                status = status.value
            elif status is None:
                status = 'queued'
            
            # 安全获取assessment_level
            assessment_level = assessment_data.get('assessment_level')
            if hasattr(assessment_level, 'value'):
                assessment_level = assessment_level.value
            
            # 先创建或获取Assessment记录
            assessment_record_id = assessment_data.get('assessment_id', 'default')
            try:
                # 尝试获取现有的Assessment记录
                existing_assessment = self.assessment_db.get_assessment(assessment_record_id)
                if not existing_assessment:
                    # 创建新的Assessment记录
                    assessment_data_for_db = {
                        'assessment_id': assessment_record_id,
                        'name': f'评估规则_{assessment_record_id}',
                        'description': '自动创建的评估规则',
                        'assessment_type': 'comprehensive',
                        'node_id': assessment_data.get('node_id', ''),
                        'channel': assessment_data.get('channel', 'B'),
                        'rubric': {},
                        'weight_idea': 0.30,
                        'weight_ui': 0.30,
                        'weight_code': 0.40,
                        'pass_threshold': 60.0,
                        'excellent_threshold': 85.0,
                        'max_retries': 3,
                        'is_active': True,
                        'version': '1.0'
                    }
                    self.assessment_db.create_assessment(assessment_data_for_db)
            except Exception as e:
                logger.warning(f"创建Assessment记录失败，使用默认记录: {str(e)}")
                assessment_record_id = 'default'
            
            # 创建AssessmentRun记录
            run_data = {
                'run_id': assessment_id,
                'student_id': assessment_data.get('student_id', ''),
                'assessment_id': assessment_record_id,
                'node_id': assessment_data.get('node_id', ''),
                'channel': assessment_data.get('channel', 'B'),
                'status': status,
                'overall_score': assessment_data.get('overall_score'),
                'idea_score': score_breakdown.get('idea'),
                'ui_score': score_breakdown.get('ui'),
                'code_score': score_breakdown.get('code'),
                'detailed_scores': assessment_data.get('detailed_scores'),
                'assessment_level': assessment_level,
                'diagnosis': assessment_data.get('diagnosis'),
                'resources': assessment_data.get('resources'),
                'exit_rules': assessment_data.get('exit_rules'),
                'error_message': assessment_data.get('error_message'),
                'started_at': assessment_data.get('started_at'),
                'completed_at': assessment_data.get('completed_at'),
                'created_at': assessment_data.get('created_at', datetime.utcnow()),
                'updated_at': assessment_data.get('updated_at', datetime.utcnow())
            }
            
            self.assessment_db.create_assessment_run(run_data)
            
            # 同时保存到文件作为备份
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
            
            # 处理ScoreBreakdown对象
            if 'score_breakdown' in data and isinstance(data['score_breakdown'], dict):
                from ..models.assessment import ScoreBreakdown
                score_breakdown_data = data['score_breakdown']
                data['score_breakdown'] = ScoreBreakdown(**score_breakdown_data)
            
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
