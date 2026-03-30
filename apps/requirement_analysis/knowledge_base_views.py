# -*- coding: utf-8 -*-
"""
知识库模块视图
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import UploadedFile
import json
import logging

from .knowledge_base_models import KnowledgeBase, KnowledgeDocument
from .knowledge_base_services import KnowledgeBaseService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def get_knowledge_base_list(request):
    """获取知识库列表"""
    try:
        knowledge_bases = KnowledgeBaseService.get_knowledge_base_list()
        data = [
            {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "is_active": kb.is_active,
                "created_at": kb.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": kb.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for kb in knowledge_bases
        ]
        return JsonResponse({"code": 200, "message": "success", "data": data})
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取知识库列表失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def create_knowledge_base(request):
    """创建知识库"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        description = data.get("description", "")
        
        if not name:
            return JsonResponse({"code": 400, "message": "知识库名称不能为空"})
        
        knowledge_base = KnowledgeBase.objects.create(
            name=name,
            description=description,
            created_by=request.user
        )
        
        return JsonResponse({
            "code": 200,
            "message": "success",
            "data": {
                "id": knowledge_base.id,
                "name": knowledge_base.name,
                "description": knowledge_base.description
            }
        })
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        return JsonResponse({"code": 500, "message": f"创建知识库失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def update_knowledge_base(request, kb_id):
    """更新知识库"""
    try:
        knowledge_base = KnowledgeBase.objects.get(id=kb_id)
        data = json.loads(request.body)
        
        if "name" in data:
            knowledge_base.name = data["name"]
        if "description" in data:
            knowledge_base.description = data["description"]
        if "is_active" in data:
            knowledge_base.is_active = data["is_active"]
        
        knowledge_base.save()
        
        return JsonResponse({"code": 200, "message": "success"})
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({"code": 404, "message": "知识库不存在"})
    except Exception as e:
        logger.error(f"更新知识库失败: {e}")
        return JsonResponse({"code": 500, "message": f"更新知识库失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def upload_document(request, kb_id):
    """上传知识库文档"""
    try:
        if "file" not in request.FILES:
            return JsonResponse({"code": 400, "message": "请选择文件"})
        
        file = request.FILES["file"]
        file_name = file.name
        
        document = KnowledgeBaseService.upload_document(kb_id, file, file_name, request.user)
        
        return JsonResponse({
            "code": 200,
            "message": "success",
            "data": {
                "id": document.id,
                "title": document.title,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "status": document.status
            }
        })
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        return JsonResponse({"code": 500, "message": f"上传文档失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def get_documents_by_knowledge_base(request, kb_id):
    """获取知识库下的文档列表"""
    try:
        documents = KnowledgeBaseService.get_documents_by_knowledge_base(kb_id)
        data = [
            {
                "id": doc.id,
                "title": doc.title,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for doc in documents
        ]
        return JsonResponse({"code": 200, "message": "success", "data": data})
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取文档列表失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def delete_document(request, doc_id):
    """删除文档"""
    try:
        document = KnowledgeDocument.objects.get(id=doc_id)
        document.delete()
        return JsonResponse({"code": 200, "message": "success"})
    except KnowledgeDocument.DoesNotExist:
        return JsonResponse({"code": 404, "message": "文档不存在"})
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return JsonResponse({"code": 500, "message": f"删除文档失败: {str(e)}"})