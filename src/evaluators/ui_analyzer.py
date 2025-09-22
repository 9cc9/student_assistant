"""UI设计分析器"""
from typing import Dict, List, Any, Optional
import logging
import base64
import io
from PIL import Image
import numpy as np

from .base import BaseEvaluator, EvaluatorError
from ..models.assessment import UIScore
from ..config.settings import get_prompts


logger = logging.getLogger(__name__)


class UIAnalyzer(BaseEvaluator):
    """UI设计分析器"""
    
    def __init__(self):
        super().__init__()
        self.prompts = get_prompts()
    
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估UI设计
        
        Args:
            data: 包含UI设计信息的字典
                - design_images: 设计图片列表（base64编码）
                - design_tool: 设计工具
                - design_system: 设计系统
                - color_palette: 色彩方案
                - prototype_url: 原型链接
                
        Returns:
            评估结果字典
        """
        try:
            # 提取数据
            design_images = data.get("ui_images", data.get("design_images", []))
            idea_text = data.get("idea_text", "")
            design_tool = data.get("design_tool", "未指定")
            design_system = data.get("design_system", "未指定")
            color_palette = data.get("color_palette", [])
            prototype_url = data.get("prototype_url", "")
            
            if not design_images:
                logger.warning("缺少UI设计图片，尝试基于创意描述进行评估。")
                return await self._evaluate_without_images(data)
            
            # 分析设计图片
            image_analysis = await self._analyze_design_images(design_images)
            
            # 构建详细提示词
            prompt = f"""
请对以下UI设计进行评估，必须严格按照JSON格式返回结果：

设计工具: {design_tool}
设计系统: {design_system}
色彩方案: {", ".join(color_palette) if color_palette else "未指定"}
图片分析: {image_analysis}

请从以下维度评估（每个维度0-100分）：

1. 易用性 (usability): 界面操作流畅度、用户友好性
2. 可访问性 (accessibility): 不同用户群体的使用便利性
3. 布局设计 (layout): 信息架构、视觉层次、界面布局

请严格按照以下JSON格式返回（不要添加任何解释）：
{{
    "usability": 数字评分,
    "accessibility": 数字评分,
    "layout": 数字评分,
    "feedback": "详细反馈文字",
    "suggestions": ["建议1", "建议2"],
    "resources": ["推荐资源1", "推荐资源2"]
}}
"""
            
            # 添加图片分析结果到提示词
            if image_analysis:
                prompt += f"\n\n图片分析结果：\n{image_analysis}"
            
            # 调用AI进行评估
            logger.info("开始评估UI设计...")
            response = await self._call_ai_api(prompt, max_tokens=1500)
            result = self._parse_json_response(response)
            
            # 验证和处理评分
            compliance_score = self._validate_score(result.get("compliance", 0))
            usability_score = self._validate_score(result.get("usability", 0))
            information_arch_score = self._validate_score(result.get("information_arch", 0))
            
            ui_score = UIScore(
                compliance=compliance_score,
                usability=usability_score,
                information_arch=information_arch_score
            )
            
            # 生成诊断信息
            feedback = result.get("feedback", "")
            suggestions = result.get("suggestions", [])
            diagnoses = self._generate_ui_diagnoses(ui_score, image_analysis)
            
            # 推荐学习资源
            resources = self._recommend_ui_resources(ui_score, design_system)
            
            logger.info(f"UI评估完成，总分: {ui_score.overall}")
            
            return {
                "score": ui_score,
                "overall_score": ui_score.overall,
                "diagnoses": diagnoses,
                "resources": resources,
                "feedback": feedback,
                "image_analysis": image_analysis,
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"UI评估失败: {str(e)}")
            raise EvaluatorError(f"UI评估失败: {str(e)}")
    
    async def _analyze_design_images(self, design_images: List[str]) -> str:
        """
        分析设计图片
        
        Args:
            design_images: base64编码的图片列表
            
        Returns:
            图片分析结果字符串
        """
        analysis_results = []
        
        for i, image_data in enumerate(design_images[:3]):  # 最多分析前3张图片
            try:
                analysis = await self._analyze_single_image(image_data)
                analysis_results.append(f"图片{i+1}: {analysis}")
            except Exception as e:
                logger.warning(f"图片{i+1}分析失败: {str(e)}")
                analysis_results.append(f"图片{i+1}: 分析失败")
        
        return "\n".join(analysis_results)
    
    async def _analyze_single_image(self, image_data: str) -> str:
        """
        分析单张图片
        
        Args:
            image_data: base64编码的图片数据
            
        Returns:
            图片分析结果
        """
        try:
            # 解码base64图片
            if image_data.startswith("data:image"):
                image_data = image_data.split(",")[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # 基本图片信息
            width, height = image.size
            aspect_ratio = width / height
            
            # 色彩分析
            color_analysis = self._analyze_colors(image)
            
            # 对比度检查（简化版）
            contrast_check = self._check_contrast(image)
            
            analysis = f"尺寸: {width}x{height}, 宽高比: {aspect_ratio:.2f}, {color_analysis}, {contrast_check}"
            
            return analysis
            
        except Exception as e:
            return f"图片分析异常: {str(e)}"
    
    def _analyze_colors(self, image: Image.Image) -> str:
        """分析图片色彩"""
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 获取主要颜色
            image_array = np.array(image)
            pixels = image_array.reshape(-1, 3)
            
            # 计算平均颜色
            avg_color = np.mean(pixels, axis=0)
            
            # 简单的色彩多样性分析
            color_std = np.std(pixels, axis=0)
            diversity = np.mean(color_std)
            
            return f"平均色彩: RGB({avg_color[0]:.0f},{avg_color[1]:.0f},{avg_color[2]:.0f}), 色彩多样性: {diversity:.1f}"
            
        except Exception:
            return "色彩分析失败"
    
    def _check_contrast(self, image: Image.Image) -> str:
        """检查对比度（简化版）"""
        try:
            # 转换为灰度图
            gray = image.convert('L')
            gray_array = np.array(gray)
            
            # 计算对比度指标
            contrast = gray_array.std()
            
            if contrast > 60:
                return "对比度: 良好"
            elif contrast > 30:
                return "对比度: 中等"
            else:
                return "对比度: 偏低，可能影响可读性"
                
        except Exception:
            return "对比度检查失败"
    
    def _generate_ui_diagnoses(self, score: UIScore, image_analysis: str) -> List:
        """生成UI诊断信息"""
        diagnoses = []
        
        if score.compliance < 70:
            diagnoses.extend(self._generate_diagnosis(
                "ui.compliance",
                ["设计规范遵循度不足"],
                ["参考平台设计指南，确保界面符合规范要求"]
            ))
        
        if score.usability < 70:
            diagnoses.extend(self._generate_diagnosis(
                "ui.usability",
                ["可用性和可访问性有待改善"],
                ["提高对比度至4.5:1以上，确保触控目标≥44pt"]
            ))
        
        if score.information_arch < 70:
            diagnoses.extend(self._generate_diagnosis(
                "ui.information_arch",
                ["信息架构和视觉层次不够清晰"],
                ["重新组织信息层次，建立清晰的视觉引导"]
            ))
        
        # 基于图片分析的诊断
        if "对比度: 偏低" in image_analysis:
            diagnoses.extend(self._generate_diagnosis(
                "ui.accessibility",
                ["对比度不足"],
                ["调整颜色方案，确保文字与背景对比度≥4.5:1"]
            ))
        
        return diagnoses
    
    def _recommend_ui_resources(self, score: UIScore, design_system: str) -> List[str]:
        """推荐UI设计资源"""
        resources = []
        
        if score.compliance < 80:
            resources.extend([
                f"{design_system}设计规范指南" if design_system != "未指定" else "Material Design设计规范",
                "平台界面设计最佳实践",
                "设计系统构建指南"
            ])
        
        if score.usability < 80:
            resources.extend([
                "可访问性设计指南",
                "用户体验设计原则",
                "色彩与对比度设计工具"
            ])
        
        if score.information_arch < 80:
            resources.extend([
                "信息架构设计方法",
                "视觉层次设计技巧",
                "界面布局最佳实践"
            ])
        
        return list(set(resources))  # 去重
    
    async def _evaluate_without_images(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        在没有UI图片的情况下基于创意描述进行评估
        """
        try:
            idea_text = data.get("idea_text", "")
            
            if not idea_text:
                logger.warning("缺少创意描述，无法进行UI评估")
                return {
                    "score": UIScore(compliance=50, usability=50, information_arch=50),
                    "overall_score": 50,
                    "diagnoses": [{
                        "dim": "UI设计",
                        "issue": "缺少UI设计图片和创意描述",
                        "fix": "请提供UI设计图片或详细的界面描述"
                    }],
                    "resources": ["UI设计基础", "用户体验设计"],
                    "feedback": "缺少UI设计材料，无法进行准确评估",
                    "raw_result": {}
                }
            
            # 基于文本描述进行简化UI评估
            prompt = f"""
请根据以下项目创意描述，对可能的UI设计进行评估：

项目描述：{idea_text}

请从以下维度评估UI设计的潜力和合理性：
1. 易用性 (0-100)：基于功能描述判断界面的易用性
2. 可访问性 (0-100)：考虑不同用户群体的使用需求
3. 布局设计 (0-100)：基于功能需求评估可能的布局合理性

请以JSON格式返回评估结果：
{{
    "usability": 评分,
    "accessibility": 评分,
    "layout": 评分,
    "feedback": "详细反馈",
    "suggestions": ["建议1", "建议2"],
    "resources": ["推荐资源1", "推荐资源2"]
}}
"""
            
            logger.info("基于创意描述进行UI评估...")
            response = await self._call_ai_api(prompt, max_tokens=1000)
            result = self._parse_json_response(response)
            
            # 处理评分
            usability_score = self._validate_score(result.get("usability", 60))
            accessibility_score = self._validate_score(result.get("accessibility", 60))
            layout_score = self._validate_score(result.get("layout", 60))
            
            ui_score = UIScore(
                compliance=usability_score,  # 把可用性映射到规范性
                usability=accessibility_score,  # 把可访问性映射到可用性
                information_arch=layout_score  # 把布局映射到信息架构
            )
            
            # 生成诊断信息
            diagnoses = []
            if ui_score.overall < 70:
                diagnoses.append({
                    "dim": "UI设计",
                    "issue": "基于项目描述的UI评估显示存在改进空间",
                    "fix": result.get("feedback", "建议完善UI设计并提供设计图片")
                })
            
            # 推荐资源
            resources = result.get("resources", [])
            if not resources:
                resources = ["UI设计基础教程", "用户体验设计原则", "界面设计最佳实践"]
            
            logger.info(f"UI评估完成（基于描述），总分: {ui_score.overall}")
            
            return {
                "score": ui_score,
                "overall_score": ui_score.overall,
                "diagnoses": diagnoses,
                "resources": resources,
                "feedback": result.get("feedback", "基于项目创意描述的UI设计评估"),
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"基于描述的UI评估失败: {str(e)}")
            # 返回默认评估
            return {
                    "score": UIScore(compliance=60, usability=60, information_arch=60),
                "overall_score": 60,
                "diagnoses": [{
                    "dim": "UI设计",
                    "issue": "UI评估失败",
                    "fix": "建议提供完整的UI设计图片和说明"
                }],
                "resources": ["UI设计基础", "用户体验设计"],
                "feedback": "UI评估过程中出现错误，给予默认评分",
                "raw_result": {}
            }


class UIAnalysisError(EvaluatorError):
    """UI分析错误"""
    pass


