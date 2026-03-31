# -*- coding: utf-8 -*-
"""
需求分析模块视图函数
"""

import json
import logging
import asyncio
import threading
import uuid
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import TestCaseGenerationTask, AIModelConfig, PromptConfig, RequirementDocument
from .ai_models import AIModelService
from .rag_services import RAGService
from .services import DocumentProcessor

logger = logging.getLogger(__name__)

def _json_error(code: int, message: str, status: int = 200):
    return JsonResponse({"code": code, "message": message}, status=status)


# -----------------------------
# 兼容前端 /requirement-analysis/api/*
# -----------------------------

@login_required
@require_http_methods(["POST"])
def api_upload_document(request):
    """
    前端兼容接口：
    POST /api/requirement-analysis/api/documents/
    """
    try:
        title = request.POST.get("title") or ""
        project_id = request.POST.get("project") or None
        file = request.FILES.get("file")

        if not file:
            return _json_error(400, "请选择文件", status=400)

        filename = (file.name or "").lower()
        if filename.endswith(".pdf"):
            doc_type = "pdf"
        elif filename.endswith((".doc", ".docx")):
            doc_type = "docx"
        elif filename.endswith(".txt"):
            doc_type = "txt"
        else:
            return _json_error(400, "不支持的文档类型，请上传 PDF/Word/TXT", status=400)

        document = RequirementDocument.objects.create(
            title=title or file.name,
            file=file,
            document_type=doc_type,
            status="uploaded",
            uploaded_by=request.user,
            project_id=project_id or None,
            file_size=getattr(file, "size", None) or 0,
        )

        return JsonResponse({"id": document.id})
    except Exception as e:
        logger.error(f"文档上传失败: {e}", exc_info=True)
        return _json_error(500, f"文档上传失败: {str(e)}", status=500)


@login_required
@require_http_methods(["GET"])
def api_extract_document_text(request, doc_id: int):
    """
    前端兼容接口：
    GET /api/requirement-analysis/api/documents/<id>/extract_text/
    """
    try:
        document = RequirementDocument.objects.get(id=doc_id, uploaded_by=request.user)
        extracted = DocumentProcessor.extract_text(document)
        document.extracted_text = extracted or ""
        document.status = "analyzed" if extracted else "failed"
        document.save(update_fields=["extracted_text", "status", "updated_at"])
        return JsonResponse({"extracted_text": document.extracted_text})
    except RequirementDocument.DoesNotExist:
        return _json_error(404, "文档不存在", status=404)
    except Exception as e:
        logger.error(f"提取文档文本失败: {e}", exc_info=True)
        return _json_error(500, f"提取失败: {str(e)}", status=500)


def _run_generation_task(
    task_id: str,
    use_writer_model: bool,
    use_reviewer_model: bool,
    knowledge_base_id: int = None,
    custom_prompt: str = ""
):
    """
    简易后台线程执行生成（不依赖 Celery）。
    """
    try:
        task = TestCaseGenerationTask.objects.select_related(
            "writer_model_config",
            "reviewer_model_config",
            "writer_prompt_config",
            "reviewer_prompt_config",
        ).get(task_id=task_id)

        task.status = "generating"
        task.progress = 30
        task.generation_log = (task.generation_log or "") + f"[{timezone.now()}] 开始生成\n"
        task.save(update_fields=["status", "progress", "generation_log", "updated_at"])

        if use_writer_model:
            generated, rag_info, writer_usage = asyncio.run(
                AIModelService.generate_test_cases(
                    task,
                    knowledge_base_id=knowledge_base_id,
                    custom_prompt=custom_prompt
                )
            )
        else:
            generated, rag_info, writer_usage = "", None, {}

        task.generated_test_cases = generated or ""
        task.rag_info = rag_info
        task.token_usage = {
            "writer": writer_usage,
            "reviewer": {},
            "total_tokens": writer_usage.get("total_tokens", 0),
        }
        task.status = "reviewing" if use_reviewer_model else "completed"
        task.progress = 70 if use_reviewer_model else 100
        task.save(update_fields=["generated_test_cases", "rag_info", "token_usage", "status", "progress", "updated_at"])

        if use_reviewer_model:
            review_feedback, reviewer_usage = asyncio.run(AIModelService.review_test_cases(task, task.generated_test_cases))
            task.review_feedback = review_feedback or ""
            task.final_test_cases = task.generated_test_cases
            task.status = "completed"
            task.progress = 100
            task.completed_at = timezone.now()
            task.token_usage = {
                "writer": writer_usage,
                "reviewer": reviewer_usage,
                "total_tokens": writer_usage.get("total_tokens", 0) + reviewer_usage.get("total_tokens", 0),
            }
            task.save(update_fields=["review_feedback", "final_test_cases", "token_usage", "status", "progress", "completed_at", "updated_at"])
        else:
            task.final_test_cases = task.generated_test_cases
            task.completed_at = timezone.now()
            task.save(update_fields=["final_test_cases", "completed_at", "updated_at"])

    except Exception as e:
        logger.error(f"生成任务执行失败 task_id={task_id}: {e}", exc_info=True)
        try:
            task = TestCaseGenerationTask.objects.get(task_id=task_id)
            task.status = "failed"
            task.error_message = str(e)
            task.progress = 0
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "error_message", "progress", "completed_at", "updated_at"])
        except Exception:
            pass


@login_required
@require_http_methods(["POST"])
def api_testcase_generation_generate(request):
    """
    前端兼容接口：
    POST /api/requirement-analysis/api/testcase-generation/generate/
    """
    try:
        data = json.loads(request.body or "{}")
        title = data.get("title") or "测试用例生成任务"
        requirement_text = data.get("requirement_text") or ""
        project_id = data.get("project") or None
        knowledge_base_id = data.get("knowledge_base_id") or None
        custom_prompt = data.get("custom_prompt") or ""
        use_writer_model = bool(data.get("use_writer_model", True))
        use_reviewer_model = bool(data.get("use_reviewer_model", True))

        if not requirement_text.strip():
            return _json_error(400, "requirement_text 不能为空", status=400)

        writer_model = AIModelConfig.objects.filter(role="writer", is_active=True).first()
        reviewer_model = AIModelConfig.objects.filter(role="reviewer", is_active=True).first()
        writer_prompt = PromptConfig.objects.filter(prompt_type="writer", is_active=True).first()
        reviewer_prompt = PromptConfig.objects.filter(prompt_type="reviewer", is_active=True).first()

        if use_writer_model and (not writer_model or not writer_prompt):
            return _json_error(400, "未配置可用的编写模型或编写提示词", status=400)
        if use_reviewer_model and (not reviewer_model or not reviewer_prompt):
            return _json_error(400, "未配置可用的评审模型或评审提示词", status=400)

        task_id = f"tcg_{uuid.uuid4().hex[:12]}"
        task = TestCaseGenerationTask.objects.create(
            task_id=task_id,
            title=title,
            requirement_text=requirement_text,
            status="pending",
            progress=0,
            project_id=project_id or None,
            writer_model_config=writer_model if use_writer_model else None,
            reviewer_model_config=reviewer_model if use_reviewer_model else None,
            writer_prompt_config=writer_prompt if use_writer_model else None,
            reviewer_prompt_config=reviewer_prompt if use_reviewer_model else None,
            created_by=request.user,
        )

        t = threading.Thread(
            target=_run_generation_task,
            args=(
                task.task_id,
                use_writer_model,
                use_reviewer_model,
                int(knowledge_base_id) if knowledge_base_id else None,
                custom_prompt,
            ),
            daemon=True,
        )
        t.start()

        return JsonResponse({"task_id": task.task_id})
    except Exception as e:
        logger.error(f"创建生成任务失败: {e}", exc_info=True)
        return _json_error(500, f"创建生成任务失败: {str(e)}", status=500)


def _task_to_frontend_payload(task: TestCaseGenerationTask):
    return {
        "task_id": task.task_id,
        "title": task.title,
        "requirement_text": task.requirement_text,
        "status": task.status,
        "progress": task.progress,
        "generated_test_cases": task.generated_test_cases,
        "review_feedback": task.review_feedback,
        "final_test_cases": task.final_test_cases,
        "error_message": task.error_message,
        "is_saved_to_records": task.is_saved_to_records,
        "rag_info": task.rag_info,
        "token_usage": task.token_usage,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
        "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M:%S") if task.updated_at else None,
        "completed_at": task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else None,
    }


@login_required
@require_http_methods(["GET"])
def api_testcase_generation_progress(request, task_id: str):
    """
    前端兼容接口：
    GET /api/requirement-analysis/api/testcase-generation/<task_id>/progress/
    """
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        return JsonResponse(_task_to_frontend_payload(task))
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


@login_required
@require_http_methods(["GET"])
def api_testcase_generation_detail(request, task_id: str):
    """
    前端兼容接口：
    GET /api/requirement-analysis/api/testcase-generation/<task_id>/
    """
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        return JsonResponse(_task_to_frontend_payload(task))
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


@login_required
@require_http_methods(["GET", "DELETE"])
def api_testcase_generation_item(request, task_id: str):
    """
    前端兼容接口：
    GET/DELETE /api/requirement-analysis/api/testcase-generation/<task_id>/
    """
    if request.method == "GET":
        return api_testcase_generation_detail(request, task_id)
    return api_testcase_generation_delete(request, task_id)


@login_required
@require_http_methods(["GET"])
def api_testcase_generation_list(request):
    """
    前端兼容接口：
    GET /api/requirement-analysis/api/testcase-generation/?page=1&page_size=10&status=completed
    """
    try:
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        status = request.GET.get("status") or None

        qs = TestCaseGenerationTask.objects.filter(created_by=request.user).order_by("-created_at")
        if status:
            qs = qs.filter(status=status)

        total = qs.count()
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        items = [_task_to_frontend_payload(t) for t in qs[start:end]]

        return JsonResponse({"count": total, "results": items})
    except Exception as e:
        logger.error(f"加载任务列表失败: {e}", exc_info=True)
        return _json_error(500, f"加载任务列表失败: {str(e)}", status=500)


@login_required
@require_http_methods(["DELETE"])
def api_testcase_generation_delete(request, task_id: str):
    """
    前端兼容接口：
    DELETE /api/requirement-analysis/api/testcase-generation/<task_id>/
    """
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        task.delete()
        return JsonResponse({"success": True})
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


@login_required
@require_http_methods(["POST"])
def api_testcase_generation_save_to_records(request, task_id: str):
    """
    前端兼容接口（简化实现）：
    POST /api/requirement-analysis/api/testcase-generation/<task_id>/save_to_records/
    """
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        if task.is_saved_to_records:
            return JsonResponse({"already_saved": True, "imported_count": 0})

        task.is_saved_to_records = True
        task.saved_at = timezone.now()
        task.save(update_fields=["is_saved_to_records", "saved_at", "updated_at"])

        return JsonResponse({"already_saved": False, "imported_count": 0})
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


def get_ai_cases(request):
    """获取AI用例生成任务列表"""
    try:
        tasks = TestCaseGenerationTask.objects.filter(created_by=request.user).order_by('-created_at')
        data = []
        for task in tasks:
            data.append({
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "status_display": task.get_status_display(),
                "total_cases": task.total_cases,
                "generated_cases": task.generated_cases,
                "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return JsonResponse({"code": 200, "message": "success", "data": data, "count": len(data), "results": data})
    except Exception as e:
        logger.error(f"获取AI用例生成任务失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI用例生成任务失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def create_ai_case(request):
    """创建AI用例生成任务"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        requirements = data.get("requirements")
        model_id = data.get("model_id")
        
        if not name or not requirements:
            return JsonResponse({"code": 400, "message": "任务名称和需求描述不能为空"})
        
        task = TestCaseGenerationTask.objects.create(
            name=name,
            requirements=requirements,
            model_id=model_id,
            status="pending",
            created_by=request.user
        )
        
        # 异步执行任务
        from .tasks import generate_test_cases_task
        generate_test_cases_task.delay(task.id)
        
        return JsonResponse({"code": 200, "message": "任务创建成功，正在生成测试用例", "data": {"id": task.id, "name": task.name}})
    except Exception as e:
        logger.error(f"创建AI用例生成任务失败: {e}")
        return JsonResponse({"code": 500, "message": f"创建AI用例生成任务失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def get_ai_case_detail(request, id):
    """获取AI用例生成任务详情"""
    try:
        task = TestCaseGenerationTask.objects.get(id=id, created_by=request.user)
        return JsonResponse({
            "code": 200,
            "message": "success",
            "data": {
                "id": task.id,
                "name": task.name,
                "requirements": task.requirements,
                "model_id": task.model_id,
                "status": task.status,
                "status_display": task.get_status_display(),
                "total_cases": task.total_cases,
                "generated_cases": task.generated_cases,
                "cases": json.loads(task.cases) if task.cases else [],
                "error_message": task.error_message,
                "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})
    except Exception as e:
        logger.error(f"获取AI用例生成任务详情失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI用例生成任务详情失败: {str(e)}"})


@login_required
@require_http_methods(["PUT"])
def update_ai_case(request, id):
    """更新AI用例生成任务"""
    try:
        task = TestCaseGenerationTask.objects.get(id=id, created_by=request.user)
        data = json.loads(request.body)
        
        if "name" in data:
            task.name = data["name"]
        if "requirements" in data:
            task.requirements = data["requirements"]
        if "model_id" in data:
            task.model_id = data["model_id"]
        
        task.save()
        return JsonResponse({"code": 200, "message": "任务更新成功", "data": {"id": task.id, "name": task.name}})
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})
    except Exception as e:
        logger.error(f"更新AI用例生成任务失败: {e}")
        return JsonResponse({"code": 500, "message": f"更新AI用例生成任务失败: {str(e)}"})


@login_required
@require_http_methods(["DELETE"])
def delete_ai_case(request, id):
    """删除AI用例生成任务"""
    try:
        task = TestCaseGenerationTask.objects.get(id=id, created_by=request.user)
        task.delete()
        return JsonResponse({"code": 200, "message": "任务删除成功"})
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})
    except Exception as e:
        logger.error(f"删除AI用例生成任务失败: {e}")
        return JsonResponse({"code": 500, "message": f"删除AI用例生成任务失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def run_ai_case(request, id):
    """运行AI用例生成任务"""
    try:
        task = TestCaseGenerationTask.objects.get(id=id, created_by=request.user)
        task.status = "pending"
        task.generated_cases = 0
        task.error_message = ""
        task.save()
        
        # 异步执行任务
        from .tasks import generate_test_cases_task
        generate_test_cases_task.delay(task.id)
        
        return JsonResponse({"code": 200, "message": "任务已重新开始执行", "data": {"id": task.id, "status": task.status}})
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})
    except Exception as e:
        logger.error(f"运行AI用例生成任务失败: {e}")
        return JsonResponse({"code": 500, "message": f"运行AI用例生成任务失败: {str(e)}"})


# RAG检索相关视图函数
@login_required
@require_http_methods(["POST"])
def rag_retrieve(request):
    """RAG检索"""
    try:
        data = json.loads(request.body)
        query = data.get("query")
        knowledge_base_id = data.get("knowledge_base_id")
        top_k = data.get("top_k", 3)
        
        if not query:
            return JsonResponse({"code": 400, "message": "查询内容不能为空"})
        
        rag_service = RAGService()
        results = rag_service.retrieve(query, knowledge_base_id, top_k)
        
        return JsonResponse({"code": 200, "message": "success", "data": results})
    except Exception as e:
        logger.error(f"RAG检索失败: {e}")
        return JsonResponse({"code": 500, "message": f"RAG检索失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def rag_generate_test_cases(request):
    """基于RAG生成测试用例"""
    try:
        data = json.loads(request.body)
        query = data.get("query")
        knowledge_base_id = data.get("knowledge_base_id")
        model_id = data.get("model_id")
        
        if not query:
            return JsonResponse({"code": 400, "message": "查询内容不能为空"})
        
        rag_service = RAGService()
        cases = rag_service.generate_test_cases(query, knowledge_base_id, model_id)
        
        return JsonResponse({"code": 200, "message": "success", "data": cases})
    except Exception as e:
        logger.error(f"基于RAG生成测试用例失败: {e}")
        return JsonResponse({"code": 500, "message": f"基于RAG生成测试用例失败: {str(e)}"})


# AI模型配置相关视图函数
@login_required
@require_http_methods(["GET"])
def get_ai_models(request):
    """获取AI模型配置列表"""
    try:
        models = AIModelConfig.objects.all()
        data = []
        for model in models:
            data.append({
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "model_type_display": model.get_model_type_display(),
                "role": model.role,
                "role_display": model.get_role_display(),
                "api_key": model.api_key[:4] + '*' * (len(model.api_key) - 8) + model.api_key[-4:] if model.api_key else '',
                "base_url": model.base_url,
                "model_name": model.model_name,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
                "is_active": model.is_active,
                "created_by": model.created_by.id,
                "created_by_name": model.created_by.username,
                "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": model.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return JsonResponse({"code": 200, "message": "success", "data": data, "count": len(data), "results": data})
    except Exception as e:
        logger.error(f"获取AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def create_ai_model(request):
    """创建AI模型配置"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        model_type = data.get("model_type")
        role = data.get("role")
        api_key = data.get("api_key")
        base_url = data.get("base_url")
        model_name = data.get("model_name")
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 4096)
        is_active = data.get("is_active", True)
        
        # 验证必填字段
        if not name or not model_type or not role or not api_key or not base_url or not model_name:
            return JsonResponse({"code": 400, "message": "请填写所有必填字段"})
        
        # 如果设置为激活，需要将同类型和角色的其他配置设置为非激活
        if is_active:
            existing = AIModelConfig.objects.filter(model_type=model_type, role=role, is_active=True).first()
            if existing:
                existing.is_active = False
                existing.save()
        
        model = AIModelConfig.objects.create(
            name=name,
            model_type=model_type,
            role=role,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            is_active=is_active,
            created_by=request.user
        )
        
        return JsonResponse({
            "code": 200,
            "message": "模型配置创建成功",
            "data": {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "model_type_display": model.get_model_type_display(),
                "role": model.role,
                "role_display": model.get_role_display(),
                "api_key": model.api_key[:4] + '*' * (len(model.api_key) - 8) + model.api_key[-4:],
                "base_url": model.base_url,
                "model_name": model.model_name,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
                "is_active": model.is_active,
                "created_by": model.created_by.id,
                "created_by_name": model.created_by.username,
                "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": model.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except Exception as e:
        logger.error(f"创建AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"创建AI模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def get_ai_model_detail(request, id):
    """获取AI模型配置详情"""
    try:
        model = AIModelConfig.objects.get(id=id)
        return JsonResponse({
            "code": 200,
            "message": "success",
            "data": {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "model_type_display": model.get_model_type_display(),
                "role": model.role,
                "role_display": model.get_role_display(),
                "api_key": model.api_key[:4] + '*' * (len(model.api_key) - 8) + model.api_key[-4:],
                "base_url": model.base_url,
                "model_name": model.model_name,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
                "is_active": model.is_active,
                "created_by": model.created_by.id,
                "created_by_name": model.created_by.username,
                "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": model.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"获取AI模型配置详情失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI模型配置详情失败: {str(e)}"})


@login_required
@require_http_methods(["PUT"])
def update_ai_model(request, id):
    """更新AI模型配置"""
    try:
        model = AIModelConfig.objects.get(id=id)
        data = json.loads(request.body)
        
        if "name" in data:
            model.name = data["name"]
        if "model_type" in data:
            model.model_type = data["model_type"]
        if "role" in data:
            model.role = data["role"]
        if "api_key" in data and data["api_key"] and '*' not in data["api_key"]:
            model.api_key = data["api_key"]
        if "base_url" in data:
            model.base_url = data["base_url"]
        if "model_name" in data:
            model.model_name = data["model_name"]
        if "temperature" in data:
            model.temperature = data["temperature"]
        if "max_tokens" in data:
            model.max_tokens = data["max_tokens"]
        if "is_active" in data:
            # 如果设置为激活，需要将同类型和角色的其他配置设置为非激活
            if data["is_active"]:
                existing = AIModelConfig.objects.filter(model_type=model.model_type, role=model.role, is_active=True).exclude(id=id).first()
                if existing:
                    existing.is_active = False
                    existing.save()
            model.is_active = data["is_active"]
        
        model.save()
        
        return JsonResponse({
            "code": 200,
            "message": "模型配置更新成功",
            "data": {
                "id": model.id,
                "name": model.name,
                "model_type": model.model_type,
                "model_type_display": model.get_model_type_display(),
                "role": model.role,
                "role_display": model.get_role_display(),
                "api_key": model.api_key[:4] + '*' * (len(model.api_key) - 8) + model.api_key[-4:],
                "base_url": model.base_url,
                "model_name": model.model_name,
                "temperature": model.temperature,
                "max_tokens": model.max_tokens,
                "is_active": model.is_active,
                "created_by": model.created_by.id,
                "created_by_name": model.created_by.username,
                "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": model.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"更新AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"更新AI模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["DELETE"])
def delete_ai_model(request, id):
    """删除AI模型配置"""
    try:
        model = AIModelConfig.objects.get(id=id)
        model.delete()
        return JsonResponse({"code": 200, "message": "模型配置删除成功"})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"删除AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"删除AI模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def test_ai_model_connection(request, id):
    """测试AI模型连接"""
    try:
        model = AIModelConfig.objects.get(id=id)
        
        # 测试模型连接
        test_text = "测试连接"
        if model.role == "writer":
            # 创建测试任务对象
            task = TestCaseGenerationTask(
                name="测试连接任务",
                requirements=test_text,
                model_id=model.id,
                writer_model_config=model,
                writer_prompt_config=PromptConfig.objects.filter(prompt_type='writer', is_active=True).first()
            )
            result = asyncio.run(AIModelService.generate_test_cases(task))
        else:
            # 创建测试任务对象
            task = TestCaseGenerationTask(
                name="测试连接任务",
                requirements=test_text,
                model_id=model.id,
                reviewer_model_config=model,
                reviewer_prompt_config=PromptConfig.objects.filter(prompt_type='reviewer', is_active=True).first()
            )
            test_cases = [{"用例标题": "测试用例", "测试步骤": "1. 打开页面\n2. 点击按钮", "预期结果": "按钮被点击"}]
            result = asyncio.run(AIModelService.review_test_cases(task, json.dumps(test_cases)))
        
        return JsonResponse({
            "code": 200,
            "message": "连接测试成功",
            "data": {
                "success": True,
                "message": "模型连接正常",
                "response": str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
            }
        })
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"测试AI模型连接失败: {e}")
        return JsonResponse({"code": 500, "message": f"连接测试失败: {str(e)}"})


# 提示词配置相关视图函数
@login_required
@require_http_methods(["GET"])
def get_prompts(request):
    """获取提示词配置列表"""
    try:
        prompts = PromptConfig.objects.all()
        data = []
        for prompt in prompts:
            data.append({
                "id": prompt.id,
                "name": prompt.name,
                "prompt_type": prompt.prompt_type,
                "prompt_type_display": prompt.get_prompt_type_display(),
                "content": prompt.content,
                "is_active": prompt.is_active,
                "created_by": prompt.created_by.id,
                "created_by_name": prompt.created_by.username,
                "created_at": prompt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": prompt.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return JsonResponse({"code": 200, "message": "success", "data": data, "count": len(data), "results": data})
    except Exception as e:
        logger.error(f"获取提示词配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取提示词配置失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def create_prompt(request):
    """创建提示词配置"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        prompt_type = data.get("prompt_type")
        content = data.get("content")
        is_active = data.get("is_active", True)
        
        # 验证必填字段
        if not name or not prompt_type or not content:
            return JsonResponse({"code": 400, "message": "请填写所有必填字段"})
        
        # 如果设置为激活，需要将同类型的其他配置设置为非激活
        if is_active:
            PromptConfig.objects.filter(prompt_type=prompt_type).update(is_active=False)
        
        prompt = PromptConfig.objects.create(
            name=name,
            prompt_type=prompt_type,
            content=content,
            is_active=is_active,
            created_by=request.user
        )
        
        return JsonResponse({
            "code": 200,
            "message": "提示词配置创建成功",
            "data": {
                "id": prompt.id,
                "name": prompt.name,
                "prompt_type": prompt.prompt_type,
                "prompt_type_display": prompt.get_prompt_type_display(),
                "content": prompt.content,
                "is_active": prompt.is_active,
                "created_by": prompt.created_by.id,
                "created_by_name": prompt.created_by.username,
                "created_at": prompt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": prompt.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except Exception as e:
        logger.error(f"创建提示词配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"创建提示词配置失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def get_prompt_detail(request, id):
    """获取提示词配置详情"""
    try:
        prompt = PromptConfig.objects.get(id=id)
        return JsonResponse({
            "code": 200,
            "message": "success",
            "data": {
                "id": prompt.id,
                "name": prompt.name,
                "prompt_type": prompt.prompt_type,
                "prompt_type_display": prompt.get_prompt_type_display(),
                "content": prompt.content,
                "is_active": prompt.is_active,
                "created_by": prompt.created_by.id,
                "created_by_name": prompt.created_by.username,
                "created_at": prompt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": prompt.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except PromptConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "提示词配置不存在"})
    except Exception as e:
        logger.error(f"获取提示词配置详情失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取提示词配置详情失败: {str(e)}"})


@login_required
@require_http_methods(["PUT"])
def update_prompt(request, id):
    """更新提示词配置"""
    try:
        prompt = PromptConfig.objects.get(id=id)
        data = json.loads(request.body)
        
        if "name" in data:
            prompt.name = data["name"]
        if "prompt_type" in data:
            prompt.prompt_type = data["prompt_type"]
        if "content" in data:
            prompt.content = data["content"]
        if "is_active" in data:
            # 如果设置为激活，需要将同类型的其他配置设置为非激活
            if data["is_active"]:
                PromptConfig.objects.filter(prompt_type=prompt.prompt_type).update(is_active=False)
            prompt.is_active = data["is_active"]
        
        prompt.save()
        
        return JsonResponse({
            "code": 200,
            "message": "更新提示词配置成功",
            "data": {
                "id": prompt.id,
                "name": prompt.name,
                "prompt_type": prompt.prompt_type,
                "prompt_type_display": prompt.get_prompt_type_display(),
                "content": prompt.content,
                "is_active": prompt.is_active,
                "created_by": prompt.created_by.id,
                "created_by_name": prompt.created_by.username,
                "created_at": prompt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": prompt.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except PromptConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "提示词配置不存在"})
    except Exception as e:
        logger.error(f"更新提示词配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"更新提示词配置失败: {str(e)}"})


@login_required
@require_http_methods(["DELETE"])
def delete_prompt(request, id):
    """删除提示词配置"""
    try:
        prompt = PromptConfig.objects.get(id=id)
        prompt.delete()
        return JsonResponse({"code": 200, "message": "删除提示词配置成功"})
    except PromptConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "提示词配置不存在"})
    except Exception as e:
        logger.error(f"删除提示词配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"删除提示词配置失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def load_default_prompts(request):
    """加载默认提示词"""
    try:
        default_prompts = {
            "writer": "你是一位专业的测试用例编写专家，擅长根据需求文档生成全面、准确、可执行的测试用例。\n\n请根据以下需求描述，按照指定的格式生成测试用例：\n\n1. 测试用例应覆盖所有功能点和边界情况\n2. 测试用例应包含：用例编号、用例标题、优先级、前置条件、测试步骤、预期结果\n3. 测试用例应具有可操作性，步骤清晰明了\n4. 测试用例应考虑各种异常情况和边界条件\n\n请严格按照上述要求生成测试用例，确保测试用例的质量和覆盖度。",
            "reviewer": "你是一位专业的测试用例评审专家，擅长评估测试用例的质量、覆盖度和可执行性。\n\n请评审以下测试用例，从以下几个方面进行评估：\n1. 测试用例是否覆盖了所有功能点和需求\n2. 测试用例是否包含了足够的边界情况和异常场景\n3. 测试用例的步骤是否清晰明了，可操作性强\n4. 测试用例的预期结果是否明确、可验证\n5. 测试用例的优先级设置是否合理\n\n请提供详细的评审意见，指出测试用例的优点和不足，并给出改进建议。"
        }
        return JsonResponse({"code": 200, "message": "success", "data": {"defaults": default_prompts}})
    except Exception as e:
        logger.error(f"加载默认提示词失败: {e}")
        return JsonResponse({"code": 500, "message": f"加载默认提示词失败: {str(e)}"})


# 向量模型配置相关视图函数
@login_required
@require_http_methods(["GET"])
def get_vector_model_config(request):
    """获取向量模型配置"""
    try:
        from django.conf import settings
        config = getattr(settings, 'VECTOR_MODEL_CONFIG', {
            'PROVIDER': 'openai',
            'MODEL': 'text-embedding-ada-002',
            'API_KEY': '',
            'API_BASE': '',
            'DIMENSION': 1536,
        })
        
        # 隐藏API密钥的部分内容
        api_key = config.get('API_KEY', '')
        masked_api_key = ''
        if api_key:
            masked_api_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
        
        return JsonResponse({
            "code": 200,
            "message": "success",
            "data": {
                "provider": config.get('PROVIDER', 'openai'),
                "model": config.get('MODEL', 'text-embedding-ada-002'),
                "api_key": masked_api_key,
                "api_base": config.get('API_BASE', ''),
                "dimension": config.get('DIMENSION', 1536),
            }
        })
    except Exception as e:
        logger.error(f"获取向量模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取向量模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def update_vector_model_config(request):
    """更新向量模型配置"""
    try:
        data = json.loads(request.body)
        provider = data.get("provider", "openai")
        model = data.get("model", "text-embedding-ada-002")
        api_key = data.get("api_key", "")
        api_base = data.get("api_base", "")
        dimension = data.get("dimension", 1536)
        
        # 验证提供商
        if provider not in ["openai", "azure", "local"]:
            return JsonResponse({"code": 400, "message": "不支持的向量模型提供商"})
        
        # 验证维度
        try:
            dimension = int(dimension)
            if dimension <= 0:
                return JsonResponse({"code": 400, "message": "向量维度必须大于0"})
        except ValueError:
            return JsonResponse({"code": 400, "message": "向量维度必须是整数"})
        
        # 获取当前配置
        from django.conf import settings
        current_config = getattr(settings, 'VECTOR_MODEL_CONFIG', {})
        
        # 如果API密钥为空或包含*，则保留原值
        if not api_key or '*' in api_key:
            api_key = current_config.get('API_KEY', '')
        
        # 更新配置
        new_config = {
            'PROVIDER': provider,
            'MODEL': model,
            'API_KEY': api_key,
            'API_BASE': api_base,
            'DIMENSION': dimension,
        }
        
        # 更新settings中的配置
        settings.VECTOR_MODEL_CONFIG = new_config
        
        # 隐藏API密钥的部分内容
        masked_api_key = ''
        if api_key:
            masked_api_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
        
        return JsonResponse({
            "code": 200,
            "message": "向量模型配置更新成功",
            "data": {
                "provider": provider,
                "model": model,
                "api_key": masked_api_key,
                "api_base": api_base,
                "dimension": dimension,
            }
        })
    except Exception as e:
        logger.error(f"更新向量模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"更新向量模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def test_vector_model_connection(request):
    """测试向量模型连接"""
    try:
        from .knowledge_base_services import EmbeddingService
        import asyncio
        
        # 获取当前配置
        config = EmbeddingService.get_vector_config()
        provider = config.get('PROVIDER', 'openai')
        api_key = config.get('API_KEY', '')
        
        if not api_key:
            return JsonResponse({"code": 400, "message": "请先配置API密钥"})
        
        # 测试获取向量嵌入
        test_text = "这是一个测试文本"
        
        # 创建新的事件循环来运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            embedding = loop.run_until_complete(EmbeddingService.get_embedding(test_text))
            loop.close()
            
            if embedding and len(embedding) > 0:
                return JsonResponse({
                    "code": 200,
                    "message": "连接测试成功",
                    "data": {
                        "provider": provider,
                        "dimension": len(embedding),
                        "sample": embedding[:5]  # 返回前5个值作为示例
                    }
                })
            else:
                return JsonResponse({"code": 500, "message": "连接测试失败：返回的向量为空"})
        except Exception as e:
            loop.close()
            raise e
            
    except Exception as e:
        logger.error(f"测试向量模型连接失败: {e}")
        return JsonResponse({"code": 500, "message": f"连接测试失败: {str(e)}"})


# -------------------------------------------------------
# 任务详情页自定义操作接口
# -------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def api_testcase_generation_batch_adopt(request, task_id: str):
    """批量采纳测试用例，保存到 testcases 表"""
    from apps.testcases.models import TestCase
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        data = json.loads(request.body or "{}")
        test_cases = data.get("test_cases", [])

        if not test_cases:
            return _json_error(400, "test_cases 不能为空", status=400)

        if not task.project:
            return _json_error(400, "该任务未关联项目，无法采纳用例。请在生成任务时选择项目。", status=400)

        created = []
        for tc in test_cases:
            obj = TestCase.objects.create(
                title=tc.get("title") or "未命名用例",
                description=tc.get("description") or "",
                preconditions=tc.get("preconditions") or "",
                steps=tc.get("steps") or "",
                expected_result=tc.get("expected_result") or "",
                priority=tc.get("priority") or "medium",
                test_type=tc.get("test_type") or "functional",
                status=tc.get("status") or "draft",
                project=task.project,
                author=request.user,
            )
            created.append(obj.id)

        return JsonResponse({"imported_count": len(created), "ids": created})
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)
    except Exception as e:
        logger.error(f"批量采纳失败: {e}", exc_info=True)
        return _json_error(500, f"批量采纳失败: {str(e)}", status=500)


@login_required
@require_http_methods(["POST"])
def api_testcase_generation_discard_selected(request, task_id: str):
    """批量弃用（从 final_test_cases 中删除指定索引的用例）"""
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        data = json.loads(request.body or "{}")
        indices = set(data.get("case_indices", []))

        if not task.final_test_cases:
            return JsonResponse({"discarded_count": 0, "updated_test_cases": ""})

        lines = task.final_test_cases.split("\n")
        # 表格格式：第0行是表头，第1行是分隔线，从第2行开始是数据
        header_lines = []
        data_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if i < 2 or not stripped:
                header_lines.append(line)
            else:
                data_lines.append(line)

        kept = [line for i, line in enumerate(data_lines) if i not in indices]
        updated = "\n".join(header_lines + kept)

        if not any(l.strip() for l in kept):
            # 全部弃用，删除任务
            task.delete()
            return JsonResponse({"task_deleted": True, "discarded_count": len(indices)})

        task.final_test_cases = updated
        task.generated_test_cases = updated
        task.save(update_fields=["final_test_cases", "generated_test_cases", "updated_at"])
        return JsonResponse({
            "discarded_count": len(indices),
            "updated_test_cases": updated,
            "task_deleted": False,
        })
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)
    except Exception as e:
        logger.error(f"批量弃用失败: {e}", exc_info=True)
        return _json_error(500, f"批量弃用失败: {str(e)}", status=500)


@login_required
@require_http_methods(["POST"])
def api_testcase_generation_discard_single(request, task_id: str):
    """弃用单条测试用例"""
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        data = json.loads(request.body or "{}")
        case_index = data.get("case_index")

        if case_index is None:
            return _json_error(400, "case_index 不能为空", status=400)

        lines = task.final_test_cases.split("\n") if task.final_test_cases else []
        header_lines = []
        data_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if i < 2 or not stripped:
                header_lines.append(line)
            else:
                data_lines.append(line)

        if case_index < len(data_lines):
            data_lines.pop(case_index)

        if not any(l.strip() for l in data_lines):
            task.delete()
            return JsonResponse({"task_deleted": True})

        updated = "\n".join(header_lines + data_lines)
        task.final_test_cases = updated
        task.generated_test_cases = updated
        task.save(update_fields=["final_test_cases", "generated_test_cases", "updated_at"])
        return JsonResponse({"task_deleted": False, "updated_test_cases": updated})
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)
    except Exception as e:
        logger.error(f"弃用用例失败: {e}", exc_info=True)
        return _json_error(500, f"弃用用例失败: {str(e)}", status=500)


@login_required
@require_http_methods(["POST"])
def api_testcase_generation_update_cases(request, task_id: str):
    """更新任务的测试用例内容"""
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        data = json.loads(request.body or "{}")
        final_test_cases = data.get("final_test_cases", "")
        task.final_test_cases = final_test_cases
        task.generated_test_cases = final_test_cases
        task.save(update_fields=["final_test_cases", "generated_test_cases", "updated_at"])
        return JsonResponse({"success": True})
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)
    except Exception as e:
        logger.error(f"更新用例失败: {e}", exc_info=True)
        return _json_error(500, f"更新用例失败: {str(e)}", status=500)
