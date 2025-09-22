"""文件上传和项目提交API"""
from fastapi import UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import asyncio

from ..services.file_service import FileService, FileProcessingError, GitProcessingError
from ..services.gateway_service import GatewayService


logger = logging.getLogger(__name__)

# 初始化服务
file_service = FileService()
gateway_service = GatewayService()


# 请求模型
class GitSubmissionRequest(BaseModel):
    """Git提交请求模型"""
    student_id: str = Field(..., description="学生ID")
    repo_url: str = Field(..., description="Git仓库URL")
    branch: str = Field(default="main", description="分支名称")
    idea_text: str = Field(..., description="项目创意描述")


class ProjectSubmissionResponse(BaseModel):
    """项目提交响应模型"""
    submission_id: str
    student_id: str
    project_path: str
    analysis: Dict[str, Any]
    assessment_id: Optional[str] = None
    message: str


async def upload_project_files(
    student_id: str = Form(...),
    idea_text: str = Form(...),
    files: List[UploadFile] = File(...)
) -> ProjectSubmissionResponse:
    """
    上传项目文件
    
    支持上传多个文件或压缩包，系统会自动解压和分析
    """
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请上传至少一个文件"
            )
        
        logger.info(f"开始处理文件上传，学生: {student_id}, 文件数: {len(files)}")
        
        # 处理上传的文件
        upload_result = await file_service.process_uploaded_files(files, student_id)
        
        # 获取项目摘要用于评估
        project_summary = file_service.get_project_summary(upload_result["upload_path"])
        
        # 构建评估请求数据
        assessment_data = {
            "student_id": student_id,
            "deliverables": {
                "idea_text": idea_text,
                "ui_images": [],  # 文件上传模式暂不支持UI图片
                "code_repo": upload_result["upload_path"],
                "code_snippets": list(project_summary["code_samples"].values())[:3]  # 取前3个文件作为代码片段
            }
        }
        
        # 提交给评估系统
        assessment_result = await gateway_service.submit_for_assessment(assessment_data)
        
        logger.info(f"项目文件上传和评估提交成功: {assessment_result['assessment_id']}")
        
        return ProjectSubmissionResponse(
            submission_id=f"upload_{upload_result['timestamp'].replace(':', '').replace('-', '')}",
            student_id=student_id,
            project_path=upload_result["upload_path"],
            analysis=upload_result["analysis"],
            assessment_id=assessment_result["assessment_id"],
            message="文件上传成功，评估已开始"
        )
        
    except FileProcessingError as e:
        logger.error(f"文件处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件处理失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传处理失败"
        )


async def submit_git_project(request: GitSubmissionRequest) -> ProjectSubmissionResponse:
    """
    通过Git仓库URL提交项目
    
    系统会克隆指定的Git仓库并进行分析评估
    """
    try:
        logger.info(f"开始处理Git仓库提交: {request.repo_url}")
        
        # 克隆Git仓库
        clone_result = await file_service.clone_git_repository(
            request.repo_url, 
            request.student_id, 
            request.branch
        )
        
        # 获取项目摘要用于评估
        project_summary = file_service.get_project_summary(clone_result["repo_path"])
        
        # 构建评估请求数据
        assessment_data = {
            "student_id": request.student_id,
            "deliverables": {
                "idea_text": request.idea_text,
                "ui_images": [],
                "code_repo": request.repo_url,  # 保持原始仓库URL
                "code_snippets": list(project_summary["code_samples"].values())[:3]
            }
        }
        
        # 提交给评估系统
        assessment_result = await gateway_service.submit_for_assessment(assessment_data)
        
        logger.info(f"Git项目提交和评估提交成功: {assessment_result['assessment_id']}")
        
        return ProjectSubmissionResponse(
            submission_id=f"git_{clone_result['timestamp'].replace(':', '').replace('-', '')}",
            student_id=request.student_id,
            project_path=clone_result["repo_path"],
            analysis=clone_result["analysis"],
            assessment_id=assessment_result["assessment_id"],
            message="Git仓库克隆成功，评估已开始"
        )
        
    except GitProcessingError as e:
        logger.error(f"Git处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Git仓库处理失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Git项目提交失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Git项目提交处理失败"
        )


async def get_project_analysis(project_path: str) -> Dict[str, Any]:
    """
    获取项目分析结果
    
    返回项目的详细分析信息，包括文件结构、技术栈等
    """
    try:
        from pathlib import Path
        
        if not Path(project_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目路径不存在"
            )
        
        # 重新分析项目（获取最新信息）
        analysis_result = await file_service._analyze_project_structure(Path(project_path))
        
        return {
            "project_path": project_path,
            "analysis": analysis_result,
            "summary": file_service.get_project_summary(project_path)
        }
        
    except Exception as e:
        logger.error(f"项目分析失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="项目分析失败"
        )


async def list_uploaded_projects(student_id: Optional[str] = None) -> Dict[str, Any]:
    """
    列出已上传的项目
    
    Args:
        student_id: 可选的学生ID过滤
        
    Returns:
        项目列表
    """
    try:
        from pathlib import Path
        
        upload_dir = Path(file_service.upload_dir)
        projects = []
        
        if student_id:
            student_dir = upload_dir / student_id
            if student_dir.exists():
                for project_dir in student_dir.iterdir():
                    if project_dir.is_dir():
                        project_info = {
                            "student_id": student_id,
                            "project_path": str(project_dir),
                            "upload_time": project_dir.name,
                            "summary": file_service.get_project_summary(str(project_dir))
                        }
                        projects.append(project_info)
        else:
            for student_dir in upload_dir.iterdir():
                if student_dir.is_dir():
                    for project_dir in student_dir.iterdir():
                        if project_dir.is_dir():
                            project_info = {
                                "student_id": student_dir.name,
                                "project_path": str(project_dir),
                                "upload_time": project_dir.name,
                                "summary": file_service.get_project_summary(str(project_dir))
                            }
                            projects.append(project_info)
        
        return {
            "total": len(projects),
            "projects": projects
        }
        
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目列表失败"
        )
