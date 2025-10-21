"""数据库配置和连接管理"""

import os
import logging
from typing import Optional
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        # 从环境变量获取数据库配置
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '3306'))
        self.username = os.getenv('DB_USERNAME', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'student_assistant')
        self.charset = os.getenv('DB_CHARSET', 'utf8mb4')
        
        # 连接池配置
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '20'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        
        # 构建连接URL
        self.url = self._build_url()
    
    def _build_url(self) -> str:
        """构建数据库连接URL"""
        return (
            f"mysql+pymysql://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?charset={self.charset}"
        )
    
    def get_engine(self) -> Engine:
        """获取数据库引擎"""
        try:
            engine = create_engine(
                self.url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # 连接前ping检查
                echo=False,  # 生产环境关闭SQL日志
                echo_pool=False,
            )
            
            # 测试连接
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info(f"📊 数据库连接成功: {self.host}:{self.port}/{self.database}")
            return engine
            
        except Exception as e:
            logger.error(f"📊 数据库连接失败: {str(e)}")
            raise


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    @property
    def engine(self) -> Engine:
        """获取数据库引擎（懒加载）"""
        if self._engine is None:
            self._engine = self.config.get_engine()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """获取会话工厂（懒加载）"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.session_factory()
    
    @contextmanager
    def get_session_context(self):
        """获取数据库会话上下文管理器"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"📊 数据库操作失败: {str(e)}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_session_context() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"📊 数据库连接测试失败: {str(e)}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("📊 数据库连接已关闭")


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db_session() -> Session:
    """获取数据库会话（用于依赖注入）"""
    return db_manager.get_session()


@contextmanager
def get_db_session_context():
    """获取数据库会话上下文管理器（用于依赖注入）"""
    with db_manager.get_session_context() as session:
        yield session
