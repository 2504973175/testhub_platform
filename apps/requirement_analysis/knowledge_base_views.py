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
from asgiref.sync import async_to_sync
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
    @async_to_sync
    async def upload_doc():
        try:
            logger.info(f"开始上传文档到知识库 {kb_id}")
            if "file" not in request.FILES:
                logger.error("没有选择文件")
                return JsonResponse({"code": 400, "message": "请选择文件"})
            
            file = request.FILES["file"]
            file_name = file.name
            logger.info(f"文件名: {file_name}, 文件大小: {file.size}")
            
            document = await KnowledgeBaseService.upload_document(kb_id, file, file_name, request.user)
            logger.info(f"文档上传成功，文档ID: {document.id}, 文档标题: {document.title}, 状态: {document.status}")
            
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
            logger.error(f"上传文档失败: {e}", exc_info=True)
            return JsonResponse({"code": 500, "message": f"上传文档失败: {str(e)}"})
    
    return upload_doc()


@login_required
@require_http_methods(["GET"])
def get_documents_by_knowledge_base(request, kb_id):
    """获取知识库下的文档列表"""
    try:
        logger.info(f"获取知识库 {kb_id} 下的文档列表")
        documents = KnowledgeBaseService.get_documents_by_knowledge_base(kb_id)
        logger.info(f"查询到 {len(documents)} 个文档")
        
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
        logger.info(f"返回文档数据: {data}")
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


@login_required
@require_http_methods(["POST"])
def delete_knowledge_base(request, kb_id):
    """删除知识库"""
    try:
        knowledge_base = KnowledgeBase.objects.get(id=kb_id)
        # 先删除知识库下的所有文档
        KnowledgeDocument.objects.filter(knowledge_base=knowledge_base).delete()
        # 再删除知识库
        knowledge_base.delete()
        return JsonResponse({"code": 200, "message": "success"})
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({"code": 404, "message": "知识库不存在"})
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        return JsonResponse({"code": 500, "message": f"删除知识库失败: {str(e)}"})