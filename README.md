# AI助教评估系统

智能化的学生作业评估平台，支持对Idea、UI设计、代码实现进行多维度评估。

## 🌟 功能特性

### 多维度智能评估
- **Idea评估(30%)**：评估创新性、可行性、学习价值
- **UI评估(30%)**：评估规范性、可用性、可访问性、信息架构
- **Code评估(40%)**：评估正确性、健壮性、可读性、可维护性、架构、性能、安全性

### 智能诊断与建议
- 详细的问题诊断和严重程度分析
- 可解释的改进建议和学习资源推荐
- 准出规则生成，支持学习路径自动调整

### 高性能处理
- 并行评估处理，支持批量任务
- 优先队列管理，支持紧急评估
- 实时状态查询和结果对比

## 🏗️ 系统架构

```
AI助教评估系统架构
┌──────────────────────────────────────────────────────────────┐
│                        API接口层                             │
│ FastAPI + Swagger │ 评估API │ 系统API │ 认证中间件              │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                        服务层                                │
│ 网关服务 → 评估服务 → (Idea | UI | Code) → 评分聚合           │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      评估引擎层                              │
│ IdeaEvaluator │ UIAnalyzer │ CodeReviewer │ ScoreAggregator   │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- pip 或 conda
- (可选) Redis, Neo4j

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd student_assistant

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# 应用配置
APP_NAME="AI助教评估系统"
DEBUG=True
ENVIRONMENT=development

# 数据库配置
DATABASE_URL="sqlite:///./student_assistant.db"
REDIS_URL="redis://localhost:6379/0"

# AI模型配置 (可选)
OPENAI_API_KEY="your-openai-api-key"
DEFAULT_MODEL="gpt-3.5-turbo"
```

### 4. 启动应用

```bash
# 开发模式启动
python -m src.main

# 或使用uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问接口

- **API文档**: http://localhost:8000/docs
- **系统状态**: http://localhost:8000/api/system/health
- **根路径**: http://localhost:8000/

## 📖 API使用示例

### 提交评估

```bash
curl -X POST "http://localhost:8000/api/assessment/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "s_20250101",
    "deliverables": {
      "idea_text": "设计一个基于AI的智能学习助手，帮助学生进行个性化学习...",
      "ui_images": ["base64://iVBORw0KGgoAAAANSUhEUgAA..."],
      "code_repo": "https://github.com/student/ai-tutor"
    },
    "title": "AI学习助手项目"
  }'
```

### 查询评估结果

```bash
curl "http://localhost:8000/api/assessment/{assessment_id}/result"
```

### 获取系统状态

```bash
curl "http://localhost:8000/api/system/status"
```

## 🔧 配置说明

### 评估器权重配置

系统支持灵活的评估权重配置：

```python
# Idea评估器权重
IDEA_EVALUATOR_CONFIG = {
    "weights": {
        "innovation": 0.4,      # 创新性
        "feasibility": 0.4,     # 可行性  
        "learning_value": 0.2   # 学习价值
    }
}

# UI分析器权重
UI_ANALYZER_CONFIG = {
    "weights": {
        "compliance": 0.25,                    # 规范性
        "usability": 0.25,                     # 可用性
        "accessibility": 0.25,                 # 可访问性
        "information_architecture": 0.25       # 信息架构
    }
}

# 代码审查器权重
CODE_REVIEWER_CONFIG = {
    "weights": {
        "correctness": 0.15,      # 正确性
        "robustness": 0.15,       # 健壮性
        "readability": 0.20,      # 可读性
        "maintainability": 0.20,  # 可维护性
        "architecture": 0.15,     # 架构设计
        "performance": 0.08,      # 性能
        "security": 0.07          # 安全性
    }
}
```

### 评分标准

- **通过标准**: 综合分≥60分
- **优秀标准**: 综合分≥85分
- **需改进**: 综合分<60分

## 🎯 评估维度详解

### Idea评估 (30%)

1. **创新性 (40%)**
   - 新颖度评估
   - 前沿性分析
   - 差异化程度

2. **可行性 (40%)**
   - 技术难度评估
   - 资源需求分析
   - 实现周期预估

3. **学习价值 (20%)**
   - 技能提升程度
   - 知识拓展范围
   - 实践应用价值

### UI评估 (30%)

1. **规范性 (25%)**
   - 平台设计规范遵循
   - 视觉一致性
   - 组件规范使用

2. **可用性与可访问性 (25%)**
   - 颜色对比度检测
   - 触控目标大小
   - 可读性分析

3. **信息架构与视觉层次 (25%)**
   - 布局合理性
   - 层级清晰度
   - 信息组织结构

### Code评估 (40%)

1. **正确性与健壮性 (30%)**
   - 语法正确性
   - 单元测试覆盖率
   - 错误处理机制

2. **可读性与可维护性 (40%)**
   - 命名规范
   - 代码结构
   - 注释完整性

3. **架构与最佳实践 (15%)**
   - 模块化设计
   - 设计模式应用
   - 接口设计质量

4. **性能与安全 (15%)**
   - 算法复杂度
   - 资源占用
   - 安全漏洞检测

## 🔌 扩展开发

### 自定义评估器

```python
from src.assessments.base import BaseEvaluator, EvaluationResult

class CustomEvaluator(BaseEvaluator):
    def _get_category(self) -> str:
        return "custom"
    
    async def evaluate(self, content, context=None) -> EvaluationResult:
        # 实现自定义评估逻辑
        pass
```

### 添加新的API端点

```python
from fastapi import APIRouter

custom_router = APIRouter(prefix="/api/custom", tags=["Custom"])

@custom_router.get("/endpoint")
async def custom_endpoint():
    return {"message": "Custom endpoint"}

# 在main.py中注册
app.include_router(custom_router)
```

## 📊 性能指标

- **评估响应时间**: <30秒 (综合评估)
- **并发处理能力**: 10个同时评估任务
- **系统可用性**: >99%
- **评估准确性**: >85% (与人工评估对比)

## 🛠️ 故障排除

### 常见问题

1. **端口占用**: 修改配置文件中的端口号
2. **依赖缺失**: 确保所有依赖已正确安装
3. **权限问题**: 检查文件系统访问权限
4. **内存不足**: 调整并发处理数量

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志  
tail -f logs/error.log
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 贡献者

感谢所有贡献者的努力！

---

**联系我们**: [项目Issue页面](https://github.com/your-org/student_assistant/issues)

**文档**: [完整文档](https://your-docs-site.com)

