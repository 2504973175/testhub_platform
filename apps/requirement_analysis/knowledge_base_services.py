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
import httpx
import json

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
    async def get_embedding(text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """获取文本的向量嵌入"""
        # 这里可以替换为实际的向量模型API调用
        # 暂时返回模拟向量
        return [0.1] * 1536
    
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
            knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id)
            
            # 确定文件类型
            file_ext = file_name.split('.')[-1].lower()
            file_type = file_ext if file_ext in ['pdf', 'docx', 'txt', 'md'] else 'other'
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex[:8]}_{file_name}"
            
            # 保存文件
            file_path = os.path.join('knowledge_base', unique_filename)
            default_storage.save(file_path, ContentFile(file.read()))
            
            # 创建文档记录
            document = KnowledgeDocument.objects.create(
                knowledge_base=knowledge_base,
                title=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file.size,
                created_by=user
            )
            
            # 异步处理文档
            asyncio.create_task(KnowledgeBaseService.process_document(document))
            
            return document
        except Exception as e:
            logger.error(f"上传文档失败: {e}")
            raise Exception(f"文档上传失败: {str(e)}")
    
    @staticmethod
    async def process_document(document: KnowledgeDocument):
        """处理文档"""
        try:
            document.status = 'processing'
            document.save()
            
            # 获取文件路径
            file_path = default_storage.path(document.file_path)
            
            # 处理文档内容
            content = DocumentProcessor.process_document(file_path, document.file_type)
            document.content = content
            
            # 生成向量嵌入
            embeddings = await EmbeddingService.chunk_and_embed(content)
            
            # 保存向量
            for embedding_data in embeddings:
                KnowledgeEmbedding.objects.create(
                    document=document,
                    chunk_text=embedding_data['chunk_text'],
                    chunk_index=embedding_data['chunk_index'],
                    embedding_vector=embedding_data['embedding_vector']
                )
            
            document.status = 'processed'
            document.save()
            
        except Exception as e:
            logger.error(f"处理文档失败: {e}")
            document.status = 'failed'
            document.save()
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
        return KnowledgeDocument.objects.filter(knowledge_base_id=knowledge_base_id).order_by('-created_at')