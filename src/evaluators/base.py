"""评估器基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import json
import asyncio
import dashscope
from dashscope import Generation

from ..config.settings import ai_config
from ..models.assessment import Diagnosis


class BaseEvaluator(ABC):
    """评估器基类"""
    
    def __init__(self):
        # 设置阿里云DashScope API密钥
        dashscope.api_key = ai_config.dashscope_api_key
        self.model = ai_config.qwen_model
    
    @abstractmethod
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估方法，由子类实现
        
        Args:
            data: 评估数据
            
        Returns:
            评估结果字典
        """
        pass
    
    async def _call_ai_api(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        调用AI API
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大token数
            
        Returns:
            AI回复文本
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 构建完整的提示词
            full_prompt = """你是一个专业的教育评估助手，请严格按照JSON格式返回评估结果。

重要要求：
1. 必须返回有效的JSON格式
2. 不要在JSON前后添加任何解释文字
3. 确保所有的键都用双引号包围
4. 确保数值类型正确

""" + prompt

            logger.info(f"🤖 准备调用AI API，提示词长度: {len(full_prompt)}")
            logger.debug(f"🤖 完整提示词: {full_prompt[:500]}...")
            
            # 调用阿里云通义千问API
            response = await self._async_call_qwen(full_prompt, max_tokens)
            
            logger.info(f"🤖 AI API调用成功，响应长度: {len(response)}")
            logger.debug(f"🤖 AI原始响应: {response[:300]}...")
            
            return response
        except Exception as e:
            logger.error(f"🤖 AI API调用失败: {str(e)}")
            raise Exception(f"AI API调用失败: {str(e)}")
    
    async def _async_call_qwen(self, prompt: str, max_tokens: int) -> str:
        """异步调用通义千问API"""
        def _sync_call():
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.1,  # 保持评估的一致性
                top_p=0.8,
                result_format='message'
            )
            
            if response.status_code == 200:
                # 正确提取响应内容
                if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                    if response.output.choices and len(response.output.choices) > 0:
                        return response.output.choices[0].message.content
                # 兼容旧格式
                elif hasattr(response, 'output') and hasattr(response.output, 'text'):
                    return response.output.text
                else:
                    raise Exception(f"响应格式异常: {response}")
            else:
                raise Exception(f"API调用失败: {response.message}")
        
        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析JSON格式的AI回复
        
        Args:
            response: AI回复文本
            
        Returns:
            解析后的字典
        """
        import re
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"📝 开始解析AI响应，长度: {len(response)}")
        logger.debug(f"📝 原始响应内容: {response}")
        
        try:
            # 清理响应内容
            cleaned_response = self._clean_ai_response(response)
            logger.info(f"📝 清理后响应长度: {len(cleaned_response)}")
            logger.debug(f"📝 清理后内容: {cleaned_response}")
            
            # 尝试直接解析JSON
            result = json.loads(cleaned_response)
            logger.info(f"📝 ✅ JSON解析成功: {list(result.keys())}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"📝 ❌ JSON直接解析失败: {str(e)}")
            logger.warning(f"📝 问题位置: 第{e.lineno}行，第{e.colno}列")
            logger.warning(f"📝 响应前500字符: {response[:500]}")
            
            # 尝试修复和提取JSON
            logger.info(f"📝 🔧 尝试修复JSON格式...")
            fixed_json = self._try_fix_json(response)
            if fixed_json:
                try:
                    result = json.loads(fixed_json)
                    logger.info(f"📝 ✅ JSON修复成功: {list(result.keys())}")
                    return result
                except json.JSONDecodeError as e2:
                    logger.warning(f"📝 ❌ 修复后仍解析失败: {str(e2)}")
            
            # 最后尝试正则提取
            logger.info(f"📝 🔍 使用正则表达式提取信息...")
            result = self._extract_info_with_regex(response)
            logger.warning(f"📝 ⚠️ 使用正则提取结果: {result}")
            return result
    
    def _clean_ai_response(self, response: str) -> str:
        """清理AI响应内容"""
        response = response.strip()
        
        # 查找JSON开始和结束位置
        json_start = response.find('{')
        json_end = response.rfind('}')
        
        if json_start != -1 and json_end > json_start:
            return response[json_start:json_end + 1]
        
        return response
    
    def _try_fix_json(self, response: str) -> str:
        """尝试修复JSON格式"""
        import re
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # 查找JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            json_str = json_match.group()
            
            # 基本清理
            json_str = json_str.replace('\n', ' ').replace('\t', ' ')
            json_str = re.sub(r'\s+', ' ', json_str)
            
            # 修复常见问题
            json_str = re.sub(r'(\w+):\s*', r'"\1": ', json_str)  # 为键添加引号
            json_str = re.sub(r':\s*([^",\[\{][^,\}\]]*?)([,\}\]])', r': "\1"\2', json_str)  # 为值添加引号
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # 移除多余逗号
            
            return json_str
            
        except Exception as e:
            logger.warning(f"JSON修复失败: {str(e)}")
            return None
    
    def _extract_info_with_regex(self, response: str) -> Dict[str, Any]:
        """使用正则表达式提取信息"""
        import re
        import logging
        
        logger = logging.getLogger(__name__)
        logger.warning("使用正则表达式解析响应")
        
        # 提取评分
        scores = re.findall(r'(?:score|评分)["\']?\s*[:=]\s*(\d+)', response, re.IGNORECASE)
        feedback_match = re.search(r'(?:feedback|反馈)["\']?\s*[:=]\s*["\']([^"\']*)["\']', response, re.IGNORECASE | re.DOTALL)
        
        return {
            "score": int(scores[0]) if scores else 70,
            "feedback": feedback_match.group(1) if feedback_match else "AI响应解析失败，给予默认反馈",
            "diagnosis": [],
            "resources": []
        }
    
    def _generate_diagnosis(self, dimension: str, issues: List[str], 
                          suggestions: List[str]) -> List[Diagnosis]:
        """
        生成诊断信息
        
        Args:
            dimension: 评估维度
            issues: 问题列表
            suggestions: 建议列表
            
        Returns:
            诊断信息列表
        """
        diagnoses = []
        for i, issue in enumerate(issues):
            fix_suggestion = suggestions[i] if i < len(suggestions) else "请参考相关最佳实践"
            diagnoses.append(Diagnosis(
                dimension=dimension,
                issue=issue,
                fix=fix_suggestion,
                priority=i + 1
            ))
        return diagnoses
    
    def _validate_score(self, score, default: int = 70) -> int:
        """
        验证和标准化评分
        
        Args:
            score: 原始评分
            default: 默认评分
            
        Returns:
            标准化后的评分(0-100)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            score_int = int(float(score))
            return max(0, min(100, score_int))
        except (ValueError, TypeError):
            logger.warning(f"无效评分值: {score}, 使用默认值: {default}")
            return default


class EvaluatorError(Exception):
    """评估器异常类"""
    pass


