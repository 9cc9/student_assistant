"""AI助教评估系统主应用"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Dict, Any
import time
from datetime import datetime
from pathlib import Path

# 导入配置和路由
from .config import get_settings
from .api import assessment_router, system_router, upload_router, learning_path_router, diagnostic_router, auth_router, student_router


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 AI助教评估系统正在启动...")
    print(f"⚙️  环境: {settings.environment}")
    print(f"🔧 调试模式: {settings.debug}")
    print(f"📊 数据库: {settings.database_url}")
    
    # 这里可以初始化数据库连接、缓存等
    # await init_database()
    # await init_cache()
    
    yield
    
    # 关闭时执行
    print("🛑 AI助教评估系统正在关闭...")
    # await cleanup_resources()


# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="""
    ## AI助教评估系统

    智能化的学生作业评估平台，支持对Idea、UI设计、代码实现进行多维度评估。

    ### 主要功能

    - **多维度评估**: 支持Idea创新性、UI可用性、代码质量的综合评估
    - **智能诊断**: 提供详细的问题诊断和改进建议
    - **个性化学习路径**: 基于入学诊断和学习进展的智能路径推荐
    - **固定节点+可变通道**: A/B/C三档任务包的个性化机制
    - **实时反馈**: 快速的评估反馈和结果查询
    - **批量处理**: 支持批量评估和对比分析

    ### API版本

    当前API版本: **v1**
    
    ### 认证

    部分API需要认证，请在请求头中包含有效的访问令牌。
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)


# 请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """添加处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Timestamp"] = datetime.now().isoformat()
    return response


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "detail": str(exc) if settings.debug else "服务暂时不可用",
            "status_code": 500,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


# 注册路由
app.include_router(assessment_router)
app.include_router(system_router)
app.include_router(upload_router)
app.include_router(learning_path_router)
app.include_router(diagnostic_router)
app.include_router(auth_router)
app.include_router(student_router)

# 静态文件服务
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# 根路径 - 重定向到前端页面
@app.get("/", tags=["Root"])
async def root():
    """系统根路径 - 返回前端页面"""
    from fastapi.responses import FileResponse
    static_dir = Path(__file__).parent.parent / "static"
    index_file = static_dir / "index.html"
    
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {
            "message": "欢迎使用AI助教评估系统",
            "version": settings.app_version,
            "environment": settings.environment,
            "docs_url": "/docs",
            "health_check": "/api/system/health",
            "timestamp": datetime.now().isoformat(),
            "features": [
                "多维度智能评估",
                "个性化学习路径推荐",
                "固定节点+可变通道机制",
                "实时反馈和诊断",
                "AI助教集成",
                "文件上传支持",
                "Git仓库集成"
            ]
        }


# API信息路径
@app.get("/info", tags=["Root"])
async def api_info() -> Dict[str, Any]:
    """API信息"""
    return {
        "api_name": settings.app_name,
        "api_version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "assessment": "/api/assessment",
            "learning_path": "/api/learning-path", 
            "system": "/api/system"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        },
        "support": {
            "health_check": "/api/system/health",
            "system_status": "/api/system/status",
            "version_info": "/api/system/version"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # 运行应用
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=True,
        log_level=settings.log_level.lower()
    )

