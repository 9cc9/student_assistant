"""API接口模块"""
from fastapi import APIRouter
from .assessment_api import (
    submit_assessment,
    get_assessment_result,
    export_path_rules,
    batch_submit_assessments,
    get_assessment_history,
    get_system_status,
    get_system_statistics,
    root as assessment_root
)
from .upload_api import (
    upload_project_files,
    submit_git_project,
    get_project_analysis,
    list_uploaded_projects
)
from .learning_path_api import (
    submit_diagnostic_assessment,
    get_student_progress,
    request_path_recommendation,
    update_node_progress,
    get_learning_path_info,
    get_available_paths,
    get_path_statistics,
    learning_path_health_check
)
from .diagnostic_api import (
    get_diagnostic_test,
    submit_diagnostic_test,
    get_diagnostic_statistics
)
from .auth_api import auth_router
from .student_api import student_router

# 创建评估路由器
assessment_router = APIRouter(prefix="/api", tags=["Assessment"])

# 注册评估相关路由
assessment_router.post("/assessment/submit")(submit_assessment)
assessment_router.get("/assessment/history")(get_assessment_history)  # 必须在 {assessment_id} 路由之前
assessment_router.get("/assessment/{assessment_id}")(get_assessment_result)
assessment_router.post("/assessment/export-path-rules")(export_path_rules)
assessment_router.post("/assessment/batch-submit")(batch_submit_assessments)

# 创建系统路由器
system_router = APIRouter(prefix="/api", tags=["System"])
system_router.get("/system/status")(get_system_status)
system_router.get("/system/statistics")(get_system_statistics)

# 创建上传路由器
upload_router = APIRouter(prefix="/api/upload", tags=["Upload"])
upload_router.post("/files")(upload_project_files)
upload_router.post("/git")(submit_git_project)
upload_router.get("/projects")(list_uploaded_projects)
upload_router.get("/analysis")(get_project_analysis)

# 创建学习路径路由器
learning_path_router = APIRouter(prefix="/api/learning-path", tags=["Learning Path"])
learning_path_router.post("/diagnostic")(submit_diagnostic_assessment)
learning_path_router.get("/progress/{student_id}")(get_student_progress)
learning_path_router.get("/recommendation/{student_id}")(request_path_recommendation)
learning_path_router.post("/progress/update")(update_node_progress)
learning_path_router.get("/path/info")(get_learning_path_info)
learning_path_router.get("/paths")(get_available_paths)
learning_path_router.get("/statistics")(get_path_statistics)
learning_path_router.get("/health")(learning_path_health_check)

# 创建诊断测试路由器
diagnostic_router = APIRouter(prefix="/api/diagnostic", tags=["Diagnostic"])
diagnostic_router.get("/test")(get_diagnostic_test)
diagnostic_router.post("/submit")(submit_diagnostic_test)
diagnostic_router.get("/statistics")(get_diagnostic_statistics)

__all__ = [
    "assessment_router",
    "system_router", 
    "upload_router",
    "learning_path_router",
    "diagnostic_router",
    "auth_router",
    "student_router"
]