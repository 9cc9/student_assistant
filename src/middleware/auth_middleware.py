"""认证中间件"""

import logging
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from ..services.auth_service import get_auth_service

logger = logging.getLogger(__name__)

# HTTP Bearer认证
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials
) -> str:
    """
    验证Token并返回学生ID
    
    Args:
        credentials: 认证凭据
        
    Returns:
        学生ID
        
    Raises:
        HTTPException: Token无效或过期
    """
    token = credentials.credentials
    auth_service = get_auth_service()
    
    valid, student_id = auth_service.verify_token(token)
    
    if not valid or not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return student_id


def get_student_id_from_token(token: str) -> Optional[str]:
    """
    从Token中获取学生ID（不抛出异常）
    
    Args:
        token: JWT Token
        
    Returns:
        学生ID或None
    """
    try:
        auth_service = get_auth_service()
        valid, student_id = auth_service.verify_token(token)
        return student_id if valid else None
    except Exception as e:
        logger.warning(f"解析Token失败: {str(e)}")
        return None


def extract_token_from_header(request: Request) -> Optional[str]:
    """
    从请求头中提取Token
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        Token或None
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    if not auth_header.startswith("Bearer "):
        return None
    
    return auth_header[7:]  # 移除"Bearer "前缀

