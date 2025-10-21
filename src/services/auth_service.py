"""学生认证服务"""

import logging
import warnings
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import os

from ..models.student_auth import StudentAccount, LoginSession, StudentStatus
from ..services.db_service import StudentDBService

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """认证服务异常"""
    pass


class AuthService:
    """
    学生认证服务
    
    提供学生注册、登录、登出、Token验证等功能
    """
    
    def __init__(self):
        """
        初始化认证服务
        """
        self.student_db = StudentDBService()
        
        # 密码加密上下文 - 抑制bcrypt版本警告
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*bcrypt.*")
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__default_rounds=12)
        
        # JWT配置
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production-2025")
        self.jwt_algorithm = "HS256"
        self.token_expire_hours = 24  # Token有效期24小时
        
        # 活跃会话存储（内存中）
        self.active_sessions: Dict[str, LoginSession] = {}
        
        logger.info("🔐 认证服务已初始化")
    
    def register(
        self, 
        student_id: str, 
        name: str, 
        password: str,
        email: Optional[str] = None
    ) -> Tuple[bool, str, Optional[StudentAccount]]:
        """
        注册新学生
        
        Args:
            student_id: 学生ID
            name: 姓名
            password: 密码
            email: 邮箱（可选）
            
        Returns:
            (成功标志, 消息, 学生账号)
        """
        try:
            # 验证学生ID唯一性
            if self._student_exists(student_id):
                return False, "学生ID已存在", None
            
            # 验证密码强度
            if len(password) < 6:
                return False, "密码长度至少6位", None
            
            # 加密密码
            password_hash = self._hash_password(password)
            
            # 创建学生数据
            student_data = {
                'student_id': student_id,
                'name': name,
                'email': email or f"{student_id}@example.com",
                'phone': None,
                'password_hash': password_hash,
                'level': 'L0',
                'learning_style': 'examples_first',
                'time_budget_hours_per_week': 6,
                'weak_skills': [],
                'interests': [],
                'goals': [],
                'mastery_scores': {},
                'frustration_level': 0.0,
                'retry_count': 0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # 保存到数据库
            db_student = self.student_db.create_student(student_data)
            
            # 创建StudentAccount对象用于返回
            student = StudentAccount(
                student_id=student_id,
                name=name,
                password_hash=password_hash,
                email=email,
                status=StudentStatus.ACTIVE,
                created_at=datetime.now()
            )
            
            logger.info(f"✅ 学生注册成功: {student_id}")
            return True, "注册成功", student
            
        except Exception as e:
            logger.error(f"❌ 注册失败: {str(e)}")
            raise AuthServiceError(f"注册失败: {str(e)}")
    
    def login(
        self, 
        student_id: str, 
        password: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str], Optional[StudentAccount]]:
        """
        学生登录
        
        Args:
            student_id: 学生ID
            password: 密码
            ip_address: IP地址
            
        Returns:
            (成功标志, 消息, Token, 学生账号)
        """
        try:
            # 检查学生是否存在并获取密码哈希
            student_data = self.student_db.get_student_for_auth(student_id)
            if not student_data:
                return False, "学生ID或密码错误", None, None
            
            # 验证密码
            if not self._verify_password(password, student_data['password_hash']):
                return False, "学生ID或密码错误", None, None
            
            # 创建StudentAccount对象用于验证
            student = StudentAccount(
                student_id=student_data['student_id'],
                name=student_data['name'],
                password_hash=student_data['password_hash'],
                email=student_data['email'],
                status=StudentStatus.ACTIVE,
                created_at=student_data['created_at']
            )
            
            # 生成JWT Token
            token = self._generate_token(student_id)
            
            # 更新最后登录时间
            self.student_db.update_student(student_id, {'updated_at': datetime.utcnow()})
            
            # 创建会话
            session = LoginSession(
                student_id=student_id,
                token=token,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.token_expire_hours),
                ip_address=ip_address
            )
            self.active_sessions[student_id] = session
            
            logger.info(f"✅ 学生登录成功: {student_id}")
            return True, "登录成功", token, student
            
        except Exception as e:
            logger.error(f"❌ 登录失败: {str(e)}")
            raise AuthServiceError(f"登录失败: {str(e)}")
    
    def logout(self, student_id: str) -> Tuple[bool, str]:
        """
        学生登出
        
        Args:
            student_id: 学生ID
            
        Returns:
            (成功标志, 消息)
        """
        try:
            if student_id in self.active_sessions:
                del self.active_sessions[student_id]
            
            logger.info(f"✅ 学生登出: {student_id}")
            return True, "已登出"
            
        except Exception as e:
            logger.error(f"❌ 登出失败: {str(e)}")
            return False, f"登出失败: {str(e)}"
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        验证Token
        
        Args:
            token: JWT Token
            
        Returns:
            (有效标志, 学生ID)
        """
        try:
            # 解析Token
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            student_id = payload.get("student_id")
            exp = payload.get("exp")
            
            # 检查是否过期
            if datetime.fromtimestamp(exp) < datetime.now():
                return False, None
            
            # 检查会话是否存在
            session = self.active_sessions.get(student_id)
            if session and session.token == token:
                return True, student_id
            
            # Token有效但会话不存在，可能是服务器重启
            # 仍然认为Token有效
            return True, student_id
            
        except JWTError as e:
            logger.warning(f"Token验证失败: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Token验证失败: {str(e)}")
            return False, None
    
    def get_student(self, student_id: str) -> Optional[StudentAccount]:
        """
        获取学生信息
        
        Args:
            student_id: 学生ID
            
        Returns:
            学生账号
        """
        try:
            db_student = self.student_db.get_student(student_id)
            if not db_student:
                return None
            
            # 转换为StudentAccount对象
            student = StudentAccount(
                student_id=db_student.student_id,
                name=db_student.name,
                password_hash="",  # 密码哈希不返回
                email=db_student.email,
                status=StudentStatus.ACTIVE,
                created_at=db_student.created_at
            )
            return student
        except Exception as e:
            logger.error(f"获取学生信息失败: {str(e)}")
            return None
    
    def update_last_login(self, student_id: str) -> bool:
        """
        更新最后登录时间
        
        Args:
            student_id: 学生ID
            
        Returns:
            是否成功
        """
        try:
            self.student_db.update_student(student_id, {'updated_at': datetime.utcnow()})
            return True
        except Exception as e:
            logger.error(f"更新登录时间失败: {str(e)}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.pwd_context.hash(password)
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return self.pwd_context.verify(password, password_hash)
        except Exception:
            return False
    
    def _generate_token(self, student_id: str) -> str:
        """生成JWT Token"""
        payload = {
            "student_id": student_id,
            "exp": datetime.now() + timedelta(hours=self.token_expire_hours),
            "iat": datetime.now()
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def _student_exists(self, student_id: str) -> bool:
        """检查学生是否存在"""
        try:
            db_student = self.student_db.get_student(student_id)
            return db_student is not None
        except Exception as e:
            logger.error(f"检查学生是否存在失败: {str(e)}")
            return False


# 创建全局单例
_auth_service = None


def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
