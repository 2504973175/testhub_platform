# -*- coding: utf-8 -*-
"""
需求分析模块URL配置
"""

from django.urls import path
from . import views
from . import knowledge_base_views

urlpatterns = [
    # AI用例生成相关
    path('ai-cases/', views.get_ai_cases, name='get_ai_cases'),
    path('ai-cases/create/', views.create_ai_case, name='create_ai_case'),
    path('ai-cases/<int:id>/', views.get_ai_case_detail, name='get_ai_case_detail'),
    path('ai-cases/<int:id>/update/', views.update_ai_case, name='update_ai_case'),
    path('ai-cases/<int:id>/delete/', views.delete_ai_case, name='delete_ai_case'),
    path('ai-cases/<int:id>/run/', views.run_ai_case, name='run_ai_case'),
    
    # 知识库相关
    path('knowledge-bases/', knowledge_base_views.get_knowledge_base_list, name='get_knowledge_base_list'),
    path('knowledge-bases/create/', knowledge_base_views.create_knowledge_base, name='create_knowledge_base'),
    path('knowledge-bases/<int:kb_id>/update/', knowledge_base_views.update_knowledge_base, name='update_knowledge_base'),
    path('knowledge-bases/<int:kb_id>/documents/', knowledge_base_views.get_documents_by_knowledge_base, name='get_documents_by_knowledge_base'),
    path('knowledge-bases/<int:kb_id>/documents/upload/', knowledge_base_views.upload_document, name='upload_document'),
    path('knowledge-bases/documents/<int:doc_id>/delete/', knowledge_base_views.delete_document, name='delete_document'),
    
    # RAG检索相关
    path('rag/retrieve/', views.rag_retrieve, name='rag_retrieve'),
    path('rag/generate-test-cases/', views.rag_generate_test_cases, name='rag_generate_test_cases'),
    
    # AI模型配置相关
    path('ai-models/', views.get_ai_models, name='get_ai_models'),
    path('ai-models/create/', views.create_ai_model, name='create_ai_model'),
    path('ai-models/<int:id>/', views.get_ai_model_detail, name='get_ai_model_detail'),
    path('ai-models/<int:id>/update/', views.update_ai_model, name='update_ai_model'),
    path('ai-models/<int:id>/delete/', views.delete_ai_model, name='delete_ai_model'),
    path('ai-models/<int:id>/test_connection/', views.test_ai_model_connection, name='test_ai_model_connection'),
]