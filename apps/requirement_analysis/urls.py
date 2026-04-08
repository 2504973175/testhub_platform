# -*- coding: utf-8 -*-
"""
需求分析模块URL配置
"""

from django.urls import path
from . import views
from . import knowledge_base_views
from . import agent_views

urlpatterns = [
    # -----------------------------
    # 兼容前端 /requirement-analysis/api/*
    # -----------------------------
    path('api/documents/', views.api_upload_document, name='api_upload_document'),
    path('api/documents/<int:doc_id>/extract_text/', views.api_extract_document_text, name='api_extract_document_text'),

    path('api/testcase-generation/', views.api_testcase_generation_list, name='api_testcase_generation_list'),
    path('api/testcase-generation/generate/', views.api_testcase_generation_generate, name='api_testcase_generation_generate'),
    path('api/testcase-generation/<str:task_id>/progress/', views.api_testcase_generation_progress, name='api_testcase_generation_progress'),
    path('api/testcase-generation/<str:task_id>/save_to_records/', views.api_testcase_generation_save_to_records, name='api_testcase_generation_save_to_records'),
    path('api/testcase-generation/<str:task_id>/batch_adopt_selected/', views.api_testcase_generation_batch_adopt, name='api_testcase_generation_batch_adopt'),
    path('api/testcase-generation/<str:task_id>/discard_selected_cases/', views.api_testcase_generation_discard_selected, name='api_testcase_generation_discard_selected'),
    path('api/testcase-generation/<str:task_id>/discard_single_case/', views.api_testcase_generation_discard_single, name='api_testcase_generation_discard_single'),
    path('api/testcase-generation/<str:task_id>/update_test_cases/', views.api_testcase_generation_update_cases, name='api_testcase_generation_update_cases'),
    path('api/testcase-generation/<str:task_id>/', views.api_testcase_generation_item, name='api_testcase_generation_item'),

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
    path('knowledge-bases/<int:kb_id>/delete/', knowledge_base_views.delete_knowledge_base, name='delete_knowledge_base'),
    path('knowledge-bases/<int:kb_id>/documents/', knowledge_base_views.get_documents_by_knowledge_base, name='get_documents_by_knowledge_base'),
    path('knowledge-bases/<int:kb_id>/documents/upload/', knowledge_base_views.upload_document, name='upload_document'),
    path('knowledge-bases/<int:kb_id>/folders/', knowledge_base_views.get_folders, name='get_folders'),
    path('knowledge-bases/<int:kb_id>/folders/create/', knowledge_base_views.create_folder, name='create_folder'),
    path('knowledge-bases/<int:kb_id>/folders/documents/', knowledge_base_views.get_documents_by_folder, name='get_documents_by_folder'),
    path('knowledge-bases/<int:kb_id>/folders/upload/', knowledge_base_views.upload_document_to_folder, name='upload_document_to_folder'),
    path('knowledge-bases/documents/<int:doc_id>/delete/', knowledge_base_views.delete_document, name='delete_document'),
    path('knowledge-bases/documents/<int:doc_id>/chunks/', knowledge_base_views.get_document_chunks, name='get_document_chunks'),
    
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
    
    # 提示词配置相关
    path('prompts/', views.get_prompts, name='get_prompts'),
    path('prompts/create/', views.create_prompt, name='create_prompt'),
    path('prompts/<int:id>/', views.get_prompt_detail, name='get_prompt_detail'),
    path('prompts/<int:id>/update/', views.update_prompt, name='update_prompt'),
    path('prompts/<int:id>/delete/', views.delete_prompt, name='delete_prompt'),
    path('prompts/load_defaults/', views.load_default_prompts, name='load_default_prompts'),
    
    # 智能体配置
    path('agents/', agent_views.list_agents, name='list_agents'),
    path('agents/create/', agent_views.create_agent, name='create_agent'),
    path('agents/<int:pk>/', agent_views.agent_detail, name='agent_detail'),
    path('agents/<int:pk>/chat/', agent_views.agent_chat, name='agent_chat'),

    # 向量模型配置相关
    path('vector-model-config/', views.get_vector_model_config, name='get_vector_model_config'),
    path('vector-model-config/update/', views.update_vector_model_config, name='update_vector_model_config'),
    path('vector-model-config/test/', views.test_vector_model_connection, name='test_vector_model_connection'),
    
    # 文档上传和提取相关
    path('documents/', knowledge_base_views.upload_document_direct, name='upload_document_direct'),
    path('documents/<int:doc_id>/extract_text/', knowledge_base_views.extract_document_text, name='extract_document_text'),
]