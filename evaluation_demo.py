#!/usr/bin/env python3
"""
AI助教评估系统 - 完整示例演示
展示如何提交一个完整的项目评估
"""

import asyncio
import json
import logging
from src.services.assessment_service import AssessmentService

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def demo_complete_assessment():
    """演示完整的项目评估流程"""
    
    print("🎯 === AI助教评估系统完整演示 ===\n")
    
    # 创建服务实例
    service = AssessmentService()
    
    # 准备一个完整的项目评估数据
    project_data = {
        # === 创意部分 ===
        "idea_text": """
        智能学习助手 - StudyBuddy
        
        项目背景：
        现在的学生在学习过程中经常遇到问题但无法及时获得帮助，特别是在课后时间。
        传统的学习方式效率低下，缺乏个性化指导。
        
        核心功能：
        1. 智能答疑：学生可以拍照提问，AI自动识别题目并给出详细解答
        2. 学习计划：根据学生的学习进度和薄弱环节，自动生成个性化学习计划
        3. 知识图谱：可视化展示知识点之间的关系，帮助学生建立完整的知识体系
        4. 学习社区：学生可以互相讨论，分享学习心得
        5. 进度跟踪：实时跟踪学习进度，提供数据分析和改进建议
        
        创新点：
        - 结合计算机视觉和自然语言处理技术
        - 个性化学习路径推荐算法
        - 多模态交互（文字、语音、图像）
        - gamification元素增强学习动机
        """,
        
        "project_name": "StudyBuddy - 智能学习助手",
        "technical_stack": ["Python", "FastAPI", "React", "TensorFlow", "OpenCV", "Neo4j"],
        "target_users": "中学生、大学生、自学者",
        "core_features": [
            "智能答疑系统",
            "个性化学习计划",
            "知识图谱可视化",
            "学习社区平台",
            "进度跟踪分析"
        ],
        
        # === UI设计部分 ===
        "ui_images": [],  # 暂时没有图片，系统会基于描述评估
        "design_tool": "Figma",
        "design_system": "Material Design 3.0",
        "color_palette": ["#1976D2", "#42A5F5", "#E3F2FD", "#37474F"],
        "prototype_url": "",
        
        # === 代码部分 ===
        "code_repo": "",
        "language": "Python",
        "framework": "FastAPI + React",
        "lines_of_code": 2500,
        "test_coverage": 75.0,
        "code_snippets": [
            """# main.py - FastAPI应用主入口
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import numpy as np
from services.ai_service import AIService
from services.ocr_service import OCRService

app = FastAPI(title="StudyBuddy API", version="1.0.0")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务实例
ai_service = AIService()
ocr_service = OCRService()

class QuestionRequest(BaseModel):
    text: str
    subject: str
    difficulty: str

@app.post("/api/ask")
async def ask_question(question: QuestionRequest):
    # 处理文字提问
    try:
        answer = await ai_service.generate_answer(
            question.text, question.subject, question.difficulty
        )
        return {"answer": answer, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))""",
            
            """# services/ai_service.py - AI服务核心逻辑
import openai
import asyncio
from typing import Dict, List
from config.settings import get_settings

settings = get_settings()

class AIService:
    # AI服务类，负责智能问答和学习建议生成
    
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = "gpt-4"
        
    async def generate_answer(self, question: str, subject: str = "通用", difficulty: str = "中等") -> Dict:
        # 生成问题答案
        try:
            prompt = self._build_answer_prompt(question, subject, difficulty)
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个耐心的老师"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            answer_content = response.choices[0].message.content
            
            return {
                "answer": answer_content,
                "subject": subject,
                "difficulty": difficulty,
                "steps": self._extract_solution_steps(answer_content)
            }
            
        except Exception as e:
            raise Exception(f"AI答案生成失败: {str(e)}")""",
            
            """# services/ocr_service.py - OCR文字识别服务
import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageEnhance

class OCRService:
    # OCR服务类，负责图片文字识别和预处理
    
    def __init__(self):
        # 支持中英文识别
        self.lang = 'chi_sim+eng'
    
    def extract_text(self, image: np.ndarray) -> str:
        # 从图片中提取文字
        try:
            # 图片预处理
            processed_image = self._preprocess_image(image)
            
            # 转换为PIL格式
            pil_image = Image.fromarray(processed_image)
            
            # 执行OCR识别
            text = pytesseract.image_to_string(
                pil_image, 
                lang=self.lang,
                config='--psm 6'
            )
            
            # 清理识别结果
            cleaned_text = self._clean_text(text)
            
            return cleaned_text
            
        except Exception as e:
            raise Exception(f"OCR识别失败: {str(e)}")"""
        ]
    }
    
    print("📝 提交项目评估...")
    print(f"项目名称: {project_data['project_name']}")
    print(f"技术栈: {', '.join(project_data['technical_stack'])}")
    print(f"代码行数: {project_data['lines_of_code']}")
    print(f"测试覆盖率: {project_data['test_coverage']}%")
    print()
    
    # 提交评估
    assessment_id = await service.submit_assessment("demo_student_001", project_data)
    print(f"✅ 评估已提交，ID: {assessment_id}")
    print("⏳ 正在进行AI评估，请稍等...")
    print()
    
    # 监控评估进度
    max_attempts = 30  # 最多等待30次，每次2秒 = 60秒
    for attempt in range(1, max_attempts + 1):
        await asyncio.sleep(2)
        
        try:
            status = service.get_assessment_status(assessment_id)
            current_status = status['status']
            
            print(f"🔄 第{attempt}次检查 - 状态: {current_status}", end="")
            
            if current_status == 'completed':
                print(" ✅")
                print()
                print("🎉 === 评估完成！结果详情 ===")
                print(f"📊 综合得分: {status['overall_score']:.1f}/100")
                print(f"📈 评估等级: {status.get('assessment_level', '未知')}")
                print()
                
                if 'breakdown' in status and status['breakdown']:
                    breakdown = status['breakdown']
                    print("📋 分项得分:")
                    print(f"  💡 创意想法: {breakdown['idea']:.1f}/100")
                    print(f"  🎨 UI设计:   {breakdown['ui']:.1f}/100") 
                    print(f"  💻 代码质量: {breakdown['code']:.1f}/100")
                    print()
                
                if 'diagnosis' in status and status['diagnosis']:
                    print("🔍 改进建议:")
                    for i, diag in enumerate(status['diagnosis'][:3], 1):  # 显示前3条
                        print(f"  {i}. [{diag['dim']}] {diag['issue']}")
                        print(f"     💡 建议: {diag['fix']}")
                        print()
                
                if 'resources' in status and status['resources']:
                    print("📚 推荐学习资源:")
                    for i, resource in enumerate(status['resources'][:5], 1):  # 显示前5个
                        print(f"  {i}. {resource}")
                    print()
                
                # 保存详细结果到文件
                result_file = "assessment_result_demo.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(status, f, indent=2, ensure_ascii=False)
                print(f"📄 详细结果已保存到: {result_file}")
                
                break
                
            elif current_status == 'failed':
                print(" ❌")
                error_msg = status.get('error_message', '未知错误')
                print(f"💥 评估失败: {error_msg}")
                break
                
            else:
                print(" ⏳")
                
        except Exception as e:
            print(f" ⚠️ 查询异常: {str(e)}")
    
    else:
        print(f"⏰ 评估超时 (等待了{max_attempts * 2}秒)")
        try:
            final_status = service.get_assessment_status(assessment_id)
            print(f"最终状态: {final_status['status']}")
        except:
            pass
    
    print("\n🎯 演示完成！")

if __name__ == "__main__":
    asyncio.run(demo_complete_assessment())
