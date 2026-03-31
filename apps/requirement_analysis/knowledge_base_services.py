# -*- coding: utf-8 -*-
"""
知识库模块服务
"""

import os
import uuid
import fitz  # PyMuPDF
import docx
import markdown
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from typing import List, Dict, Any, Optional
import logging
import asyncio
import threading
import httpx
import json
from asgiref.sync import sync_to_async

from .knowledge_base_models import KnowledgeBase, KnowledgeDocument, KnowledgeEmbedding

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理类"""
    
    @staticmethod
    def process_pdf(file_path: str) -> str:
        """处理PDF文档"""
        content = []
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text = page.get_text()
                content.append(text)
            doc.close()
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"处理PDF文档失败: {e}")
            raise Exception(f"PDF处理失败: {str(e)}")
    
    @staticmethod
    def process_docx(file_path: str) -> str:
        """处理Word文档"""
        content = []
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                content.append(para.text)
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"处理Word文档失败: {e}")
            raise Exception(f"Word文档处理失败: {str(e)}")
    
    @staticmethod
    def process_txt(file_path: str) -> str:
        """处理文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"处理文本文件失败: {e}")
            raise Exception(f"文本文件处理失败: {str(e)}")
    
    @staticmethod
    def process_md(file_path: str) -> str:
        """处理Markdown文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
                # 转换为纯文本
                html = markdown.markdown(md_content)
                # 简单去除HTML标签
                text = ''.join(html.split('<')[0] for html in html.split('>'))
                return text
        except Exception as e:
            logger.error(f"处理Markdown文件失败: {e}")
            raise Exception(f"Markdown文件处理失败: {str(e)}")
    
    @staticmethod
    def process_document(file_path: str, file_type: str) -> str:
        """根据文件类型处理文档"""
        processors = {
            'pdf': DocumentProcessor.process_pdf,
            'docx': DocumentProcessor.process_docx,
            'txt': DocumentProcessor.process_txt,
            'md': DocumentProcessor.process_md,
        }
        
        if file_type in processors:
            return processors[file_type](file_path)
        else:
            raise Exception(f"不支持的文件类型: {file_type}")


class EmbeddingService:
    """向量嵌入服务"""
    
    @staticmethod
    def get_vector_config():
        """获取向量模型配置"""
        from django.conf import settings
        return getattr(settings, 'VECTOR_MODEL_CONFIG', {
            'PROVIDER': 'openai',
            'MODEL': 'text-embedding-ada-002',
            'API_KEY': '',
            'API_BASE': '',
            'DIMENSION': 1536,
        })
    
    @staticmethod
    async def get_embedding(text: str, model: str = None) -> List[float]:
        """获取文本的向量嵌入"""
        config = EmbeddingService.get_vector_config()
        provider = config.get('PROVIDER', 'openai')
        api_key = config.get('API_KEY', '')
        api_base = config.get('API_BASE', '')
        dimension = config.get('DIMENSION', 1536)
        model_name = model or config.get('MODEL', 'text-embedding-ada-002')
        
        # 如果没有配置API密钥，返回模拟向量
        if not api_key:
            logger.warning(f"向量模型API密钥未配置，使用模拟向量。提供商: {provider}")
            return [0.1] * dimension
        
        try:
            if provider == 'openai':
                return await EmbeddingService._get_openai_embedding(text, model_name, api_key, api_base)
            elif provider == 'azure':
                return await EmbeddingService._get_azure_embedding(text, model_name, api_key, api_base)
            elif provider == 'local':
                return await EmbeddingService._get_local_embedding(text, model_name, api_base)
            else:
                logger.warning(f"不支持的向量模型提供商: {provider}，使用模拟向量")
                return [0.1] * dimension
        except Exception as e:
            logger.error(f"获取向量嵌入失败: {e}")
            return [0.1] * dimension
    
    @staticmethod
    async def _get_openai_embedding(text: str, model: str, api_key: str, api_base: str = None) -> List[float]:
        """调用OpenAI API获取向量嵌入"""
        import httpx
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        base_url = api_base or 'https://api.openai.com/v1'
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{base_url}/embeddings',
                headers=headers,
                json={
                    'input': text,
                    'model': model
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['embedding']
    
    @staticmethod
    async def _get_azure_embedding(text: str, model: str, api_key: str, api_base: str) -> List[float]:
        """调用Azure OpenAI API获取向量嵌入"""
        import httpx
        
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{api_base}/openai/deployments/{model}/embeddings?api-version=2023-05-15',
                headers=headers,
                json={'input': text},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['embedding']
    
    @staticmethod
    async def _get_local_embedding(text: str, model: str, api_base: str) -> List[float]:
        """调用本地向量模型服务获取向量嵌入"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{api_base}/embeddings',
                json={'text': text, 'model': model},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data['embedding']
    
    @staticmethod
    async def chunk_and_embed(text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
        """将文本分块并生成向量"""
        chunks = []
        text_length = len(text)
        start = 0
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap
        
        embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = await EmbeddingService.get_embedding(chunk)
            embeddings.append({
                'chunk_text': chunk,
                'chunk_index': i,
                'embedding_vector': embedding
            })
        
        return embeddings


class KnowledgeBaseService:
    """知识库服务类"""
    
    @staticmethod
    async def upload_document(knowledge_base_id: int, file: Any, file_name: str, user: Any) -> KnowledgeDocument:
        """上传知识库文档"""
        try:
            logger.info(f"开始上传文档，知识库ID: {knowledge_base_id}, 文件名: {file_name}")
            
            # 使用sync_to_async包装同步的数据库操作
            get_knowledge_base = sync_to_async(KnowledgeBase.objects.get)
            knowledge_base = await get_knowledge_base(id=knowledge_base_id)
            logger.info(f"找到知识库: {knowledge_base.name}, ID: {knowledge_base.id}")
            
            # 确定文件类型
            file_ext = file_name.split('.')[-1].lower()
            file_type = file_ext if file_ext in ['pdf', 'docx', 'txt', 'md'] else 'other'
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex[:8]}_{file_name}"
            
            # 保存文件
            file_path = os.path.join('knowledge_base', unique_filename)
            default_storage.save(file_path, ContentFile(file.read()))
            logger.info(f"文件已保存到: {file_path}")
            
            # 使用sync_to_async包装同步的数据库操作
            create_document = sync_to_async(KnowledgeDocument.objects.create)
            document = await create_document(
                knowledge_base=knowledge_base,
                title=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file.size,
                created_by=user
            )
            logger.info(f"文档记录已创建，文档ID: {document.id}, 知识库ID: {document.knowledge_base_id}")
            
            # 后台线程异步处理文档，避免请求上下文结束导致任务丢失
            t = threading.Thread(
                target=KnowledgeBaseService.process_document_in_background,
                args=(document.id,),
                daemon=True
            )
            t.start()
            
            return document
        except Exception as e:
            logger.error(f"上传文档失败: {e}", exc_info=True)
            raise Exception(f"文档上传失败: {str(e)}")

    @staticmethod
    def process_document_in_background(document_id: int):
        """在线程中运行异步文档处理任务"""
        asyncio.run(KnowledgeBaseService.process_document_by_id(document_id))

    @staticmethod
    async def process_document_by_id(document_id: int):
        """按ID加载文档并进行处理，避免跨上下文对象问题"""
        get_document = sync_to_async(
            KnowledgeDocument.objects.select_related("knowledge_base").get
        )
        document = await get_document(id=document_id)
        await KnowledgeBaseService.process_document(document)
    
    @staticmethod
    async def process_document(document: KnowledgeDocument):
        """处理文档"""
        try:
            # 使用sync_to_async包装同步的数据库操作
            save_document = sync_to_async(document.save)
            document.status = 'processing'
            await save_document()
            
            # 获取文件路径
            file_path = default_storage.path(document.file_path)
            
            # 处理文档内容
            content = DocumentProcessor.process_document(file_path, document.file_type)
            document.content = content
            
            # 生成向量嵌入
            embeddings = await EmbeddingService.chunk_and_embed(content)
            
            # 保存向量
            create_embedding = sync_to_async(KnowledgeEmbedding.objects.create)
            for embedding_data in embeddings:
                await create_embedding(
                    document=document,
                    chunk_text=embedding_data['chunk_text'],
                    chunk_index=embedding_data['chunk_index'],
                    embedding_vector=embedding_data['embedding_vector']
                )
            
            document.status = 'processed'
            await save_document()
            
        except Exception as e:
            logger.error(f"处理文档失败: {e}")
            document.status = 'failed'
            save_document = sync_to_async(document.save)
            await save_document()
            raise Exception(f"文档处理失败: {str(e)}")
    
    @staticmethod
    def get_knowledge_base_list() -> List[KnowledgeBase]:
        """获取知识库列表"""
        return KnowledgeBase.objects.filter(is_active=True).order_by('-created_at')
    
    @staticmethod
    def get_knowledge_base(knowledge_base_id: int) -> KnowledgeBase:
        """获取知识库详情"""
        return KnowledgeBase.objects.get(id=knowledge_base_id)
    
    @staticmethod
    def get_documents_by_knowledge_base(knowledge_base_id: int) -> List[KnowledgeDocument]:
        """获取知识库下的文档列表"""
        logger.info(f"查询知识库 {knowledge_base_id} 的文档列表")
        documents = KnowledgeDocument.objects.filter(knowledge_base_id=knowledge_base_id).order_by('-created_at')
        logger.info(f"查询结果: 找到 {len(documents)} 个文档")
        for doc in documents:
            logger.info(f"  - 文档ID: {doc.id}, 标题: {doc.title}, 知识库ID: {doc.knowledge_base_id}")
        return documents