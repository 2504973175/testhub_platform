# -*- coding: utf-8 -*-
"""
RAG检索服务
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging
import asyncio
from sklearn.metrics.pairwise import cosine_similarity

from .knowledge_base_models import KnowledgeBase, KnowledgeDocument, KnowledgeEmbedding, RAGQueryRecord
from .knowledge_base_services import EmbeddingService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG检索服务类"""
    
    @staticmethod
    async def retrieve_relevant_documents(query: str, knowledge_base_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关文档"""
        try:
            # 获取查询向量
            query_embedding = await EmbeddingService.get_embedding(query)
            
            # 获取知识库中的所有向量
            embeddings = KnowledgeEmbedding.objects.filter(
                document__knowledge_base_id=knowledge_base_id,
                document__status='processed'
            ).select_related('document')
            
            if not embeddings:
                return []
            
            # 计算相似度
            similarities = []
            for embedding in embeddings:
                embedding_vector = np.array(embedding.embedding_vector).reshape(1, -1)
                query_vector = np.array(query_embedding).reshape(1, -1)
                similarity = cosine_similarity(query_vector, embedding_vector)[0][0]
                similarities.append((similarity, embedding))
            
            # 按相似度排序
            similarities.sort(reverse=True, key=lambda x: x[0])
            
            # 获取top_k结果
            top_results = similarities[:top_k]
            
            # 构建返回结果
            relevant_chunks = []
            for similarity, embedding in top_results:
                relevant_chunks.append({
                    'document_id': embedding.document.id,
                    'document_title': embedding.document.title,
                    'chunk_index': embedding.chunk_index,
                    'chunk_text': embedding.chunk_text,
                    'similarity': float(similarity)
                })
            
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"RAG检索失败: {e}")
            raise Exception(f"RAG检索失败: {str(e)}")
    
    @staticmethod
    async def augment_query_with_rag(query: str, knowledge_base_id: int, top_k: int = 5) -> str:
        """使用RAG增强查询"""
        try:
            # 检索相关文档
            relevant_chunks = await RAGService.retrieve_relevant_documents(query, knowledge_base_id, top_k)
            
            if not relevant_chunks:
                return query
            
            # 构建增强后的查询
            augmented_query = f"请根据以下知识库内容和用户需求生成测试用例：\n\n"
            augmented_query += "知识库内容：\n"
            for i, chunk in enumerate(relevant_chunks):
                augmented_query += f"【文档{i+1}】{chunk['document_title']}\n"
                augmented_query += f"{chunk['chunk_text']}\n\n"
            
            augmented_query += f"用户需求：{query}\n"
            
            return augmented_query
            
        except Exception as e:
            logger.error(f"查询增强失败: {e}")
            return query
    
    @staticmethod
    async def save_query_record(query: str, knowledge_base_id: int, relevant_chunks: List[Dict[str, Any]], user: Any) -> RAGQueryRecord:
        """保存查询记录"""
        try:
            query_record = RAGQueryRecord.objects.create(
                query_text=query,
                knowledge_base_id=knowledge_base_id,
                retrieved_chunks=relevant_chunks,
                created_by=user
            )
            return query_record
        except Exception as e:
            logger.error(f"保存查询记录失败: {e}")
            return None
    
    @staticmethod
    async def rag_retrieval_and_augment(query: str, knowledge_base_id: int, user: Any, top_k: int = 5) -> str:
        """完整的RAG检索和增强流程"""
        try:
            # 检索相关文档
            relevant_chunks = await RAGService.retrieve_relevant_documents(query, knowledge_base_id, top_k)
            
            # 保存查询记录
            await RAGService.save_query_record(query, knowledge_base_id, relevant_chunks, user)
            
            # 增强查询
            augmented_query = await RAGService.augment_query_with_rag(query, knowledge_base_id, top_k)
            
            return augmented_query
            
        except Exception as e:
            logger.error(f"RAG流程失败: {e}")
            return query