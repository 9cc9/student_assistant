"""学生学习进度的数据库访问仓储"""

from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import text

from ..config.database import get_db_session_context
from ..models.learning_path import Channel, NodeStatus


class ProgressRepository:
    """封装 student_progress 与 student_progress_nodes 的读写操作"""

    @staticmethod
    def get_student_progress(student_id: str) -> Optional[Dict[str, Any]]:
        """读取学生全局进度与节点进度集合"""
        with get_db_session_context() as session:
            sp = session.execute(
                text(
                    """
                    SELECT student_id, current_node_id, current_channel, total_study_hours, frustration_level,
                           started_at, last_activity_at, updated_at
                    FROM student_progress
                    WHERE student_id = :sid
                    """
                ),
                {"sid": student_id},
            ).mappings().first()

            if not sp:
                return None

            nodes = session.execute(
                text(
                    """
                    SELECT node_id, status, used_channel, score, attempt_count, started_at, completed_at
                    FROM student_progress_nodes
                    WHERE student_id = :sid
                    """
                ),
                {"sid": student_id},
            ).mappings().all()

            return {
                "progress": dict(sp),
                "nodes": [dict(n) for n in nodes],
            }

    @staticmethod
    def upsert_student_progress(
        student_id: str,
        current_node_id: str,
        current_channel: Channel,
        total_study_hours: float,
        frustration_level: float,
        started_at: datetime,
        last_activity_at: datetime,
    ) -> None:
        """插入或更新学生全局进度"""
        with get_db_session_context() as session:
            session.execute(
                text(
                    """
                    INSERT INTO student_progress (
                        student_id, current_node_id, current_channel, total_study_hours,
                        frustration_level, started_at, last_activity_at
                    ) VALUES (:sid, :nid, :ch, :hours, :fru, :started, :last)
                    ON DUPLICATE KEY UPDATE
                        current_node_id = VALUES(current_node_id),
                        current_channel = VALUES(current_channel),
                        total_study_hours = VALUES(total_study_hours),
                        frustration_level = VALUES(frustration_level),
                        last_activity_at = VALUES(last_activity_at)
                    """
                ),
                {
                    "sid": student_id,
                    "nid": current_node_id,
                    "ch": current_channel.value,
                    "hours": total_study_hours,
                    "fru": frustration_level,
                    "started": started_at,
                    "last": last_activity_at,
                },
            )

    @staticmethod
    def update_student_progress(progress) -> None:
        """更新学生进度（接受StudentPathProgress对象）"""
        with get_db_session_context() as session:
            session.execute(
                text(
                    """
                    UPDATE student_progress 
                    SET current_node_id = :nid,
                        current_channel = :ch,
                        total_study_hours = :hours,
                        frustration_level = :fru,
                        last_activity_at = :last,
                        updated_at = :updated
                    WHERE student_id = :sid
                    """
                ),
                {
                    "sid": progress.student_id,
                    "nid": progress.current_node_id,
                    "ch": progress.current_channel.value,
                    "hours": progress.total_study_hours,
                    "fru": progress.frustration_level,
                    "last": progress.last_activity_at,
                    "updated": progress.updated_at,
                },
            )

    @staticmethod
    def upsert_node_progress(
        student_id: str,
        node_id: str,
        status: NodeStatus,
        used_channel: Optional[Channel],
        score: Optional[float],
        attempt_count: int,
        started_at: Optional[datetime],
        completed_at: Optional[datetime],
    ) -> None:
        """插入或更新某个节点的进度"""
        with get_db_session_context() as session:
            session.execute(
                text(
                    """
                    INSERT INTO student_progress_nodes (
                        student_id, node_id, status, used_channel, score, attempt_count, started_at, completed_at
                    ) VALUES (:sid, :nid, :st, :uch, :score, :attempts, :started, :completed)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        used_channel = VALUES(used_channel),
                        score = VALUES(score),
                        attempt_count = VALUES(attempt_count),
                        started_at = VALUES(started_at),
                        completed_at = VALUES(completed_at)
                    """
                ),
                {
                    "sid": student_id,
                    "nid": node_id,
                    "st": status.value,
                    "uch": used_channel.value if used_channel else None,
                    "score": score,
                    "attempts": attempt_count,
                    "started": started_at,
                    "completed": completed_at,
                },
            )

    @staticmethod
    def clear_student_progress(student_id: str) -> None:
        """清除学生的学习进度数据"""
        with get_db_session_context() as session:
            # 删除学生进度节点记录
            session.execute(
                text(
                    """
                    DELETE FROM student_progress_nodes 
                    WHERE student_id = :sid
                    """
                ),
                {"sid": student_id},
            )
            
            # 删除学生全局进度记录
            session.execute(
                text(
                    """
                    DELETE FROM student_progress 
                    WHERE student_id = :sid
                    """
                ),
                {"sid": student_id},
            )


