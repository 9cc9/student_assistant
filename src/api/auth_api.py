"""学生认证API接口"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Body
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from ..services.auth_service import get_auth_service, AuthServiceError
from ..middleware.auth_middleware import security, verify_token

logger = logging.getLogger(__name__)

# 创建路由器
auth_router = APIRouter(prefix="/api/auth", tags=["认证"])


# ============ 请求模型 ============

class RegisterRequest(BaseModel):
    """注册请求模型"""
    student_id: str = Field(..., description="学生ID", min_length=3, max_length=50)
    name: str = Field(..., description="姓名", min_length=1, max_length=100)
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    email: Optional[str] = Field(None, description="邮箱")
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "s_20250101",
                "name": "张三",
                "password": "password123",
                "email": "zhangsan@example.com"
            }
        }


class LoginRequest(BaseModel):
    """登录请求模型"""
    student_id: str = Field(..., description="学生ID")
    password: str = Field(..., description="密码")
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "s_20250101",
                "password": "password123"
            }
        }


# ============ API端点 ============

@auth_router.post("/register", summary="学生注册")
async def register(request: RegisterRequest):
    """
    学生注册
    
    创建新的学生账号
    """
    try:
        auth_service = get_auth_service()
        
        success, message, student = auth_service.register(
            student_id=request.student_id,
            name=request.name,
            password=request.password,
            email=request.email
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return JSONResponse(
            content={
                "success": True,
                "message": message,
                "student": {
                    "student_id": student.student_id,
                    "name": student.name,
                    "email": student.email,
                    "created_at": student.created_at.isoformat()
                }
            },
            status_code=201
        )
        
    except AuthServiceError as e:
        logger.error(f"注册失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.post("/login", summary="学生登录")
async def login(request_data: LoginRequest, req: Request):
    """
    学生登录
    
    验证学生身份并返回JWT Token
    """
    try:
        auth_service = get_auth_service()
        
        # 获取客户端IP
        client_ip = req.client.host if req.client else None
        
        success, message, token, student = auth_service.login(
            student_id=request_data.student_id,
            password=request_data.password,
            ip_address=client_ip
        )
        
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        return JSONResponse(
            content={
                "success": True,
                "message": message,
                "token": token,
                "student": {
                    "student_id": student.student_id,
                    "name": student.name,
                    "email": student.email,
                    "created_at": student.created_at.isoformat(),
                    "last_login": student.last_login.isoformat() if student.last_login else None
                }
            }
        )
        
    except AuthServiceError as e:
        logger.error(f"登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.post("/logout", summary="学生登出")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    学生登出
    
    注销当前会话
    """
    try:
        # 验证Token并获取学生ID
        student_id = await verify_token(credentials)
        
        auth_service = get_auth_service()
        success, message = auth_service.logout(student_id)
        
        return JSONResponse(
            content={
                "success": success,
                "message": message
            }
        )
        
    except Exception as e:
        logger.error(f"登出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.get("/verify", summary="验证Token")
async def verify(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    验证Token是否有效
    
    返回Token的有效性和学生ID
    """
    try:
        student_id = await verify_token(credentials)
        
        return JSONResponse(
            content={
                "valid": True,
                "student_id": student_id
            }
        )
        
    except HTTPException:
        # Token无效
        return JSONResponse(
            content={
                "valid": False,
                "student_id": None
            },
            status_code=200  # 返回200，但valid为false
        )


@auth_router.get("/me", summary="获取当前用户信息")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    获取当前登录的学生信息
    """
    try:
        student_id = await verify_token(credentials)
        
        auth_service = get_auth_service()
        student = auth_service.get_student(student_id)
        
        if not student:
            raise HTTPException(status_code=404, detail="学生信息不存在")
        
        return JSONResponse(
            content={
                "student_id": student.student_id,
                "name": student.name,
                "email": student.email,
                "status": student.status.value,
                "created_at": student.created_at.isoformat(),
                "last_login": student.last_login.isoformat() if student.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
