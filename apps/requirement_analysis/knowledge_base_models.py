# -*- coding: utf-8 -*-
"""
知识库模块模型
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import datetime

User = get_user_model()

# 生成文档ID
def generate_document_id():
    return f'doc_{uuid.uuid4().hex[:8]}'

# 生成向量ID
def generate_embedding_id():
    return f'emb_{uuid.uuid4().hex[:8]}'

# 生成查询ID
def generate_query_id():
    return f'query_{uuid.uuid4().hex[:8]}'


class KnowledgeBase(models.Model):
    """知识库模型"""
    name = models.CharField(max_length=200, verbose_name='知识库名称')
    description = models.TextField(blank=True, verbose_name='知识库描述')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    
    class Meta:
        db_table = 'knowledge_base'
        verbose_name = '知识库'
        verbose_name_plural = '知识库'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class KnowledgeDocument(models.Model):
    """知识库文档模型"""
    DOCUMENT_TYPE_CHOICES = [
        ('pdf', 'PDF文档'),
        ('docx', 'Word文档'),
        ('txt', '文本文件'),
        ('md', 'Markdown文件'),
        ('other', '其他类型'),
    ]
    
    STATUS_CHOICES = [
        ('uploaded', '已上传'),
        ('processing', '处理中'),
        ('processed', '已处理'),
        ('failed', '处理失败'),
    ]
    
    document_id = models.CharField(max_length=50, unique=True, default=generate_document_id, verbose_name='文档ID')
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='documents', verbose_name='所属知识库')
    title = models.CharField(max_length=200, verbose_name='文档标题')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    file_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, verbose_name='文件类型')
    file_size = models.IntegerField(verbose_name='文件大小(字节)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded', verbose_name='处理状态')
    content = models.TextField(blank=True, verbose_name='文档内容')
    metadata = models.JSONField(default=dict, verbose_name='元数据')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='上传者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'knowledge_document'
        verbose_name = '知识库文档'
        verbose_name_plural = '知识库文档'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class KnowledgeEmbedding(models.Model):
    """知识库向量模型"""
    embedding_id = models.CharField(max_length=50, unique=True, default=generate_embedding_id, verbose_name='向量ID')
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='embeddings', verbose_name='所属文档')
    chunk_text = models.TextField(verbose_name='文本片段')
    chunk_index = models.IntegerField(verbose_name='片段索引')
    embedding_vector = models.JSONField(verbose_name='向量表示')
    metadata = models.JSONField(default=dict, verbose_name='元数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'knowledge_embedding'
        verbose_name = '知识库向量'
        verbose_name_plural = '知识库向量'
        ordering = ['document', 'chunk_index']
    
    def __str__(self):
        return f"{self.document.title} - 片段{self.chunk_index}"


class RAGQueryRecord(models.Model):
    """RAG查询记录模型"""
    query_id = models.CharField(max_length=50, unique=True, default=generate_query_id, verbose_name='查询ID')
    query_text = models.TextField(verbose_name='查询文本')
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.SET_NULL, null=True, verbose_name='使用的知识库')
    retrieved_documents = models.JSONField(default=list, verbose_name='检索到的文档')
    retrieved_chunks = models.JSONField(default=list, verbose_name='检索到的文本片段')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='查询用户')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='查询时间')
    
    class Meta:
        db_table = 'rag_query_record'
        verbose_name = 'RAG查询记录'
        verbose_name_plural = 'RAG查询记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"查询{self.query_id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"