"""学生认证服务"""

import logging
import warnings
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import os
import json
from pathlib import Path

from ..models.student_auth import StudentAccount, LoginSession, StudentStatus

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """认证服务异常"""
    pass


class AuthService:
    """
    学生认证服务
    
    提供学生注册、登录、登出、Token验证等功能
    """
    
    def __init__(self, storage_path: str = "./data/students"):
        """
        初始化认证服务
        
        Args:
            storage_path: 学生数据存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
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
            
            # 创建学生账号
            student = StudentAccount(
                student_id=student_id,
                name=name,
                password_hash=password_hash,
                email=email,
                status=StudentStatus.ACTIVE,
                created_at=datetime.now()
            )
            
            # 保存学生信息
            self._save_student(student)
            
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
            # 检查学生是否存在
            student = self._load_student(student_id)
            if not student:
                return False, "学生ID或密码错误", None, None
            
            # 验证密码
            if not self._verify_password(password, student.password_hash):
                return False, "学生ID或密码错误", None, None
            
            # 检查账号状态
            if student.status != StudentStatus.ACTIVE:
                return False, f"账号状态异常: {student.status.value}", None, None
            
            # 生成JWT Token
            token = self._generate_token(student_id)
            
            # 更新最后登录时间
            student.last_login = datetime.now()
            self._save_student(student)
            
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
        return self._load_student(student_id)
    
    def update_last_login(self, student_id: str) -> bool:
        """
        更新最后登录时间
        
        Args:
            student_id: 学生ID
            
        Returns:
            是否成功
        """
        try:
            student = self._load_student(student_id)
            if student:
                student.last_login = datetime.now()
                self._save_student(student)
                return True
            return False
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
        student_file = self.storage_path / f"{student_id}.json"
        return student_file.exists()
    
    def _save_student(self, student: StudentAccount) -> None:
        """保存学生信息"""
        student_file = self.storage_path / f"{student.student_id}.json"
        data = student.to_dict()
        data["password_hash"] = student.password_hash  # 保存密码哈希
        
        with open(student_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_student(self, student_id: str) -> Optional[StudentAccount]:
        """加载学生信息"""
        student_file = self.storage_path / f"{student_id}.json"
        if not student_file.exists():
            return None
        
        try:
            with open(student_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return StudentAccount.from_dict(data)
        except Exception as e:
            logger.error(f"加载学生信息失败: {str(e)}")
            return None


# 创建全局单例
_auth_service = None


def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
