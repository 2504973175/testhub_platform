# -*- coding: utf-8 -*-
"""
AI模型配置和服务
"""

from django.contrib.auth import get_user_model
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
import logging

from .models import AIModelConfig, PromptConfig, TestCaseGenerationTask

User = get_user_model()
logger = logging.getLogger(__name__)


class AIModelService:
    """AI模型服务类"""
    
    @staticmethod
    async def call_openai_compatible_api(config: AIModelConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用OpenAI兼容格式的API"""
        headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': config.model_name,
            'messages': messages,
            'max_tokens': config.max_tokens,
            'temperature': config.temperature,
            'top_p': config.top_p,
            'stream': False
        }
        
        # 确保base_url不以/结尾
        base_url = config.base_url.rstrip('/')
        # 如果用户没有输入完整的v1/chat/completions路径，尝试智能补全
        if not base_url.endswith('/chat/completions'):
            if base_url.endswith('/v1'):
                url = f"{base_url}/chat/completions"
            else:
                # 默认假设是根路径，尝试添加 v1/chat/completions
                # 但对于某些API（如DeepSeek），base_url可能已经是 https://api.deepseek.com
                url = f"{base_url}/v1/chat/completions"
        else:
            url = base_url
            
        try:
            # Increase timeout to 120s for long generation tasks
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=data
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"API调用返回错误: Status={response.status_code}, Body={error_detail}")
                    
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            provider_name = config.get_model_type_display()
            error_msg = f"{provider_name} API返回错误 {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.TimeoutException as e:
            provider_name = config.get_model_type_display()
            logger.error(f"{provider_name} API请求超时: {repr(e)}")
            raise Exception(f"{provider_name} API请求超时，请稍后再试或检查网络连接")
        except Exception as e:
            provider_name = config.get_model_type_display()
            # Use repr(e) to capture the full exception type and message, especially if str(e) is empty
            logger.error(f"{provider_name} API调用失败: {repr(e)}")
            raise Exception(f"{provider_name} API调用失败: {str(e) or repr(e)}")
    
    @staticmethod
    async def call_deepseek_api(config: AIModelConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用DeepSeek API (兼容OpenAI格式)"""
        return await AIModelService.call_openai_compatible_api(config, messages)
    
    @staticmethod
    async def call_qwen_api(config: AIModelConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用千问API (兼容OpenAI格式)"""
        return await AIModelService.call_openai_compatible_api(config, messages)
    
    @staticmethod
    async def generate_test_cases(
        task: TestCaseGenerationTask,
        knowledge_base_id: Optional[int] = None,
        custom_prompt: Optional[str] = None
    ):
        """生成测试用例，返回 (content, rag_info) 元组"""
        rag_info = None
        user_message = f"请根据以下需求生成测试用例：\n\n{task.requirement_text}"

        # 调用腾讯云 LKE 智能体
        from .tencent_agent import call_lke_agent
        logger.info(f"开始调用 LKE 智能体，user_message 长度={len(user_message)}")
        content, usage = await call_lke_agent(user_message)
        logger.info(f"LKE 智能体返回内容长度={len(content)}")
        return content, rag_info, usage
    
    @staticmethod
    async def review_test_cases(task: TestCaseGenerationTask, test_cases: str):
        """评审测试用例，返回 (content, usage) 元组"""
        user_message = f"请评审以下测试用例：\n\n{test_cases}"

        from .tencent_agent import call_lke_agent
        content, usage = await call_lke_agent(user_message)
        return content, usage