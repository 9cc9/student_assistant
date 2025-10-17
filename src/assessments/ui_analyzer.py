"""UI分析器"""

import time
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
from io import BytesIO
from PIL import Image
import cv2
import numpy as np

from .base import BaseEvaluator, EvaluationResult
from ..models import ScoreBreakdown, Diagnosis, ScoreDimension


class UIAnalyzer(BaseEvaluator):
    """UI分析器 - 评估规范性、可用性、可访问性、信息架构"""
    
    WEIGHTS = {
        ScoreDimension.UI_COMPLIANCE: 0.25,              # 规范性 25%
        ScoreDimension.UI_USABILITY: 0.25,               # 可用性 25%
        ScoreDimension.UI_ACCESSIBILITY: 0.25,           # 可访问性 25%
        ScoreDimension.UI_INFORMATION_ARCHITECTURE: 0.25 # 信息架构 25%
    }
    
    def _get_category(self) -> str:
        return "ui"
    
    async def evaluate(self, content: Any, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        """评估UI设计"""
        start_time = time.time()
        
        # 解析输入内容
        images = self._parse_ui_content(content)
        if not images:
            raise ValueError("未找到有效的UI图片")
        
        # 分析所有图片
        analysis_results = []
        for i, image in enumerate(images):
            analysis = await self._analyze_ui_image(image, f"image_{i}")
            analysis_results.append(analysis)
        
        # 综合分析结果
        combined_analysis = self._combine_analysis_results(analysis_results)
        
        # 生成各维度评分
        breakdown = [
            await self._evaluate_compliance(combined_analysis),
            await self._evaluate_usability(combined_analysis),
            await self._evaluate_accessibility(combined_analysis),
            await self._evaluate_information_architecture(combined_analysis)
        ]
        
        # 计算总分
        overall_score = self._calculate_score(breakdown)
        
        # 生成诊断
        diagnosis = self._generate_diagnosis(breakdown, combined_analysis)
        
        # 收集证据
        evidence = self._collect_evidence(combined_analysis)
        
        processing_time = time.time() - start_time
        
        return EvaluationResult(
            category=self.category,
            overall_score=overall_score,
            breakdown=breakdown,
            diagnosis=diagnosis,
            evidence=evidence,
            processing_time=processing_time,
            created_at=datetime.now()
        )
    
    def _parse_ui_content(self, content: Any) -> List[np.ndarray]:
        """解析UI内容，支持base64图片、文件路径等"""
        images = []
        
        if isinstance(content, str):
            # 处理base64编码的图片
            if content.startswith('data:image/') or content.startswith('base64://'):
                try:
                    # 提取base64数据
                    if content.startswith('data:image/'):
                        base64_data = content.split(',')[1]
                    else:
                        base64_data = content.replace('base64://', '')
                    
                    # 解码图片
                    img_data = base64.b64decode(base64_data)
                    pil_image = Image.open(BytesIO(img_data))
                    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    images.append(opencv_image)
                except Exception as e:
                    print(f"解析base64图片失败: {e}")
        
        elif isinstance(content, list):
            # 处理图片列表
            for item in content:
                images.extend(self._parse_ui_content(item))
        
        return images
    
    async def _analyze_ui_image(self, image: np.ndarray, image_name: str) -> Dict[str, Any]:
        """分析单个UI图片"""
        height, width = image.shape[:2]
        
        # 颜色分析
        color_analysis = self._analyze_colors(image)
        
        # 布局分析
        layout_analysis = self._analyze_layout(image)
        
        # 文字识别(简单的轮廓检测)
        text_analysis = self._analyze_text_elements(image)
        
        # 控件检测
        ui_elements = self._detect_ui_elements(image)
        
        return {
            "image_name": image_name,
            "dimensions": {"width": width, "height": height},
            "colors": color_analysis,
            "layout": layout_analysis,
            "text": text_analysis,
            "ui_elements": ui_elements,
            "aspect_ratio": width / height
        }
    
    def _analyze_colors(self, image: np.ndarray) -> Dict[str, Any]:
        """分析颜色使用"""
        # 转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 计算主要颜色
        pixels = rgb_image.reshape(-1, 3)
        
        # 计算颜色多样性
        unique_colors = len(np.unique(pixels.view(np.dtype((np.void, pixels.dtype.itemsize * pixels.shape[1])))))
        total_pixels = len(pixels)
        color_diversity = unique_colors / total_pixels
        
        # 亮度分析
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        brightness_std = np.std(gray)
        
        # 对比度分析
        contrast_ratio = self._calculate_contrast_ratio(gray)
        
        return {
            "diversity": color_diversity,
            "mean_brightness": mean_brightness,
            "brightness_variance": brightness_std,
            "contrast_ratio": contrast_ratio,
            "has_good_contrast": contrast_ratio > 4.5  # WCAG标准
        }
    
    def _calculate_contrast_ratio(self, gray_image: np.ndarray) -> float:
        """计算对比度比率(简化版本)"""
        # 计算最亮和最暗像素的对比度
        max_luminance = np.max(gray_image) / 255.0
        min_luminance = np.min(gray_image) / 255.0
        
        # 防止除以零
        if min_luminance == 0:
            min_luminance = 0.05
        
        return (max_luminance + 0.05) / (min_luminance + 0.05)
    
    def _analyze_layout(self, image: np.ndarray) -> Dict[str, Any]:
        """分析布局结构"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 检测直线(网格结构)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        line_count = len(lines) if lines is not None else 0
        
        # 检测矩形区域
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rectangles = []
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                rectangles.append(approx)
        
        # 计算白空间比例
        white_pixels = np.sum(gray > 240)
        total_pixels = gray.size
        whitespace_ratio = white_pixels / total_pixels
        
        return {
            "grid_lines": line_count,
            "rectangular_regions": len(rectangles),
            "whitespace_ratio": whitespace_ratio,
            "has_good_spacing": whitespace_ratio > 0.1,
            "structured_layout": line_count > 5
        }
    
    def _analyze_text_elements(self, image: np.ndarray) -> Dict[str, Any]:
        """分析文本元素"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 文本检测(基于形态学操作)
        # 创建矩形结构元素用于检测水平文本线
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        
        # 查找文本区域
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤文本区域
        text_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            area = cv2.contourArea(contour)
            
            # 文本区域通常是水平矩形
            if aspect_ratio > 2 and area > 100:
                text_regions.append((x, y, w, h))
        
        return {
            "text_regions_count": len(text_regions),
            "has_hierarchical_text": len(text_regions) > 2,
            "text_regions": text_regions
        }
    
    def _detect_ui_elements(self, image: np.ndarray) -> Dict[str, Any]:
        """检测UI元素"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 检测圆形按钮
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=10, maxRadius=50)
        circle_count = len(circles[0]) if circles is not None else 0
        
        # 检测矩形按钮/卡片
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        cards = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:  # 太小的忽略
                continue
                
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            
            # 按钮: 小面积，接近正方形或横向矩形
            if area < 5000 and 0.5 <= aspect_ratio <= 4:
                buttons.append((x, y, w, h))
            # 卡片: 较大面积的矩形
            elif area > 2000 and 0.7 <= aspect_ratio <= 3:
                cards.append((x, y, w, h))
        
        return {
            "circles": circle_count,
            "buttons": len(buttons),
            "cards": len(cards),
            "interactive_elements": circle_count + len(buttons),
            "has_sufficient_touch_targets": len(buttons) > 0
        }
    
    def _combine_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个图片的分析结果"""
        if not results:
            return {}
        
        combined = {
            "image_count": len(results),
            "total_area": sum(r["dimensions"]["width"] * r["dimensions"]["height"] for r in results),
            "avg_contrast_ratio": np.mean([r["colors"]["contrast_ratio"] for r in results]),
            "good_contrast_ratio": all(r["colors"]["has_good_contrast"] for r in results),
            "avg_whitespace": np.mean([r["layout"]["whitespace_ratio"] for r in results]),
            "structured_layouts": sum(1 for r in results if r["layout"]["structured_layout"]),
            "total_text_regions": sum(r["text"]["text_regions_count"] for r in results),
            "total_interactive_elements": sum(r["ui_elements"]["interactive_elements"] for r in results),
            "consistent_aspect_ratios": self._check_aspect_ratio_consistency(results)
        }
        
        return combined
    
    def _check_aspect_ratio_consistency(self, results: List[Dict[str, Any]]) -> bool:
        """检查界面宽高比的一致性"""
        if len(results) <= 1:
            return True
        
        aspect_ratios = [r["aspect_ratio"] for r in results]
        std_dev = np.std(aspect_ratios)
        return std_dev < 0.2  # 标准差小于0.2认为是一致的
    
    async def _evaluate_compliance(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估设计规范性"""
        base_score = 70
        
        # 一致性加分
        consistency_score = 15 if analysis.get("consistent_aspect_ratios", False) else -10
        
        # 结构化布局
        structure_score = min(analysis.get("structured_layouts", 0) * 5, 15)
        
        total_score = min(base_score + consistency_score + structure_score, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if not analysis.get("consistent_aspect_ratios", False):
            issues.append("界面尺寸比例不一致")
            suggestions.append("保持界面尺寸比例的一致性，遵循平台设计规范")
        
        if analysis.get("structured_layouts", 0) < analysis.get("image_count", 1) / 2:
            issues.append("布局结构不够规范")
            suggestions.append("使用网格系统，建立清晰的视觉层次")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.UI_COMPLIANCE,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.UI_COMPLIANCE],
            evidence=[f"一致性: {analysis.get('consistent_aspect_ratios', False)}", f"结构化布局: {analysis.get('structured_layouts', 0)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_usability(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估可用性"""
        base_score = 65
        
        # 交互元素充足性
        interactive_score = min(analysis.get("total_interactive_elements", 0) * 2, 20)
        
        # 空白空间合理性
        whitespace_score = 15 if 0.1 <= analysis.get("avg_whitespace", 0) <= 0.4 else -10
        
        total_score = min(base_score + interactive_score + whitespace_score, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if analysis.get("total_interactive_elements", 0) < 3:
            issues.append("交互元素数量不足")
            suggestions.append("增加必要的交互控件，如按钮、输入框等")
        
        if analysis.get("avg_whitespace", 0) < 0.05:
            issues.append("界面过于拥挤")
            suggestions.append("增加适当的空白空间，改善视觉体验")
        elif analysis.get("avg_whitespace", 0) > 0.5:
            issues.append("空白空间过多")
            suggestions.append("更好地利用界面空间，增加有用的内容或功能")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.UI_USABILITY,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.UI_USABILITY],
            evidence=[f"交互元素: {analysis.get('total_interactive_elements', 0)}", f"空白比例: {analysis.get('avg_whitespace', 0):.2f}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_accessibility(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估可访问性"""
        base_score = 60
        
        # 对比度评分
        contrast_score = 25 if analysis.get("good_contrast_ratio", False) else -20
        
        # 触控目标大小(简化判断)
        touch_target_score = 15 if analysis.get("total_interactive_elements", 0) > 0 else -10
        
        total_score = min(base_score + contrast_score + touch_target_score, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if not analysis.get("good_contrast_ratio", False):
            issues.append("颜色对比度不足")
            suggestions.append("确保文本与背景对比度≥4.5:1，重要内容≥7:1")
        
        if analysis.get("avg_contrast_ratio", 0) < 3:
            issues.append("整体对比度偏低")
            suggestions.append("增强颜色对比，提高可读性")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.UI_ACCESSIBILITY,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.UI_ACCESSIBILITY],
            evidence=[f"对比度比率: {analysis.get('avg_contrast_ratio', 0):.2f}", f"通过对比度测试: {analysis.get('good_contrast_ratio', False)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    async def _evaluate_information_architecture(self, analysis: Dict[str, Any]) -> ScoreBreakdown:
        """评估信息架构与视觉层次"""
        base_score = 65
        
        # 文本层次
        hierarchy_score = min(analysis.get("total_text_regions", 0) * 3, 20) if analysis.get("total_text_regions", 0) > 1 else -10
        
        # 视觉组织
        organization_score = 15 if analysis.get("structured_layouts", 0) > 0 else -10
        
        total_score = min(base_score + hierarchy_score + organization_score, 100)
        total_score = max(total_score, 0)
        
        issues = []
        suggestions = []
        
        if analysis.get("total_text_regions", 0) <= 1:
            issues.append("缺乏清晰的信息层次")
            suggestions.append("建立清晰的标题、副标题、正文层次结构")
        
        if analysis.get("structured_layouts", 0) == 0:
            issues.append("视觉组织缺乏结构")
            suggestions.append("使用对齐、分组等方式组织信息")
        
        return ScoreBreakdown(
            dimension=ScoreDimension.UI_INFORMATION_ARCHITECTURE,
            score=total_score,
            weight=self.WEIGHTS[ScoreDimension.UI_INFORMATION_ARCHITECTURE],
            evidence=[f"文本区域: {analysis.get('total_text_regions', 0)}", f"结构化布局: {analysis.get('structured_layouts', 0)}"],
            issues=issues,
            suggestions=suggestions
        )
    
    def _calculate_score(self, breakdown: List[ScoreBreakdown]) -> float:
        """计算加权总分"""
        total_score = 0
        for item in breakdown:
            total_score += item.score * item.weight
        return round(total_score, 1)
    
    def _generate_diagnosis(self, breakdown: List[ScoreBreakdown], analysis: Dict[str, Any]) -> List[Diagnosis]:
        """生成诊断结果"""
        diagnosis = []
        
        for item in breakdown:
            for issue in item.issues:
                severity = "major"
                if item.score < 50:
                    severity = "critical"
                elif item.score > 75:
                    severity = "minor"
                
                # 找到对应的建议
                suggestion_idx = item.issues.index(issue)
                fix = item.suggestions[suggestion_idx] if suggestion_idx < len(item.suggestions) else "需要改进"
                
                diagnosis.append(Diagnosis(
                    dimension=item.dimension,
                    issue=issue,
                    fix=fix,
                    priority=1 if severity == "critical" else 2 if severity == "major" else 3
                ))
        
        return diagnosis
    
    def _collect_evidence(self, analysis: Dict[str, Any]) -> List[str]:
        """收集评估证据"""
        evidence = [
            f"分析图片数量: {analysis.get('image_count', 0)}",
            f"平均对比度: {analysis.get('avg_contrast_ratio', 0):.2f}",
            f"平均空白比例: {analysis.get('avg_whitespace', 0):.2f}",
            f"交互元素总数: {analysis.get('total_interactive_elements', 0)}",
            f"文本区域总数: {analysis.get('total_text_regions', 0)}"
        ]
        
        if analysis.get("good_contrast_ratio", False):
            evidence.append("✓ 通过对比度测试")
        if analysis.get("consistent_aspect_ratios", False):
            evidence.append("✓ 尺寸比例一致")
        if analysis.get("structured_layouts", 0) > 0:
            evidence.append("✓ 具有结构化布局")
        
        return evidence

