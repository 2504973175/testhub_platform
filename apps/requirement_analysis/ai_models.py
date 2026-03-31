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
        writer_prompt = (custom_prompt or "").strip() or task.writer_prompt_config.content
        rag_info = None

        # 如果提供了知识库ID，使用RAG增强查询
        if knowledge_base_id:
            from .rag_services import RAGService
            from .knowledge_base_models import KnowledgeBase
            from asgiref.sync import sync_to_async

            if str(knowledge_base_id) == 'all':
                # 检索所有知识库
                all_kbs = await sync_to_async(list)(KnowledgeBase.objects.filter(is_active=True))
                all_chunks = []
                for kb in all_kbs:
                    chunks = await RAGService.retrieve_relevant_documents(task.requirement_text, kb.id, top_k=3)
                    all_chunks.extend(chunks)
                # 按相似度排序取 top 5
                all_chunks.sort(key=lambda x: x['similarity'], reverse=True)
                relevant_chunks = all_chunks[:5]
                kb_name = '所有知识库'
            else:
                relevant_chunks = await RAGService.retrieve_relevant_documents(
                    task.requirement_text, knowledge_base_id
                )
                try:
                    kb = await sync_to_async(KnowledgeBase.objects.get)(id=knowledge_base_id)
                    kb_name = kb.name
                except Exception:
                    kb_name = f"知识库#{knowledge_base_id}"

            augmented_query = await RAGService.augment_query_with_rag(
                task.requirement_text, knowledge_base_id if str(knowledge_base_id) != 'all' else (all_kbs[0].id if all_kbs else None)
            ) if str(knowledge_base_id) != 'all' else task.requirement_text
            if str(knowledge_base_id) == 'all' and relevant_chunks:
                from .rag_services import RAGService as _RS
                augmented_query = await _RS.augment_query_with_rag_chunks(task.requirement_text, relevant_chunks)
            user_message = augmented_query

            rag_info = {
                "knowledge_base_id": knowledge_base_id,
                "knowledge_base_name": kb_name,
                "chunk_count": len(relevant_chunks),
                "chunks": [
                    {
                        "document_title": c["document_title"],
                        "chunk_index": c["chunk_index"],
                        "chunk_text": c["chunk_text"],
                        "similarity": round(c["similarity"], 4),
                    }
                    for c in relevant_chunks
                ],
            }
        else:
            user_message = f"请根据以下需求生成测试用例：\n\n{task.requirement_text}"

        messages = [
            {"role": "system", "content": writer_prompt},
            {"role": "user", "content": user_message}
        ]

        # 所有支持的模型都使用兼容OpenAI的接口
        response = await AIModelService.call_openai_compatible_api(task.writer_model_config, messages)
        content = response['choices'][0]['message']['content']
        usage = response.get('usage', {})
        return content, rag_info, usage
    
    @staticmethod
    async def review_test_cases(task: TestCaseGenerationTask, test_cases: str):
        """评审测试用例，返回 (content, usage) 元组"""
        reviewer_prompt = task.reviewer_prompt_config.content
        user_message = f"请评审以下测试用例：\n\n{test_cases}"

        messages = [
            {"role": "system", "content": reviewer_prompt},
            {"role": "user", "content": user_message}
        ]

        response = await AIModelService.call_openai_compatible_api(task.reviewer_model_config, messages)
        content = response['choices'][0]['message']['content']
        usage = response.get('usage', {})
        return content, usage