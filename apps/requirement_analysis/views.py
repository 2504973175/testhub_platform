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
    """POST /api/requirement-analysis/api/documents/"""
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
    """GET /api/requirement-analysis/api/documents/<id>/extract_text/"""
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


def _run_generation_task(task_id, use_writer_model, use_reviewer_model, knowledge_base_id=None, custom_prompt=""):
    """简易后台线程执行生成（不依赖 Celery）"""
    try:
        task = TestCaseGenerationTask.objects.select_related(
            "writer_model_config", "reviewer_model_config",
            "writer_prompt_config", "reviewer_prompt_config",
        ).get(task_id=task_id)

        task.status = "generating"
        task.progress = 30
        task.started_at = timezone.now()
        task.generation_log = (task.generation_log or "") + f"[{timezone.now()}] 开始生成\n"
        task.save(update_fields=["status", "progress", "started_at", "generation_log", "updated_at"])

        if use_writer_model:
            generated, rag_info, writer_usage = asyncio.run(
                AIModelService.generate_test_cases(task, knowledge_base_id=knowledge_base_id, custom_prompt=custom_prompt)
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
    """POST /api/requirement-analysis/api/testcase-generation/generate/"""
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

        task_id = f"tcg_{uuid.uuid4().hex[:12]}"
        task = TestCaseGenerationTask.objects.create(
            task_id=task_id, title=title, requirement_text=requirement_text,
            status="pending", progress=0, project_id=project_id or None,
            writer_model_config=None,
            reviewer_model_config=None,
            writer_prompt_config=None,
            reviewer_prompt_config=None,
            created_by=request.user,
        )

        t = threading.Thread(
            target=_run_generation_task,
            args=(task.task_id, use_writer_model, use_reviewer_model,
                  int(knowledge_base_id) if knowledge_base_id else None, custom_prompt),
            daemon=True,
        )
        t.start()
        return JsonResponse({"task_id": task.task_id})
    except Exception as e:
        logger.error(f"创建生成任务失败: {e}", exc_info=True)
        return _json_error(500, f"创建生成任务失败: {str(e)}", status=500)


def _fmt_dt(dt):
    """将 UTC datetime 转为本地时间字符串"""
    if not dt:
        return None
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")


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
        "created_at": _fmt_dt(task.created_at),
        "updated_at": _fmt_dt(task.updated_at),
        "started_at": _fmt_dt(task.started_at),
        "completed_at": _fmt_dt(task.completed_at),
        "duration_seconds": round((task.completed_at - task.started_at).total_seconds()) if task.completed_at and task.started_at else None,
    }


@login_required
@require_http_methods(["GET"])
def api_testcase_generation_progress(request, task_id: str):
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        return JsonResponse(_task_to_frontend_payload(task))
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


@login_required
@require_http_methods(["GET"])
def api_testcase_generation_detail(request, task_id: str):
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        return JsonResponse(_task_to_frontend_payload(task))
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


@login_required
@require_http_methods(["GET", "DELETE"])
def api_testcase_generation_item(request, task_id: str):
    if request.method == "GET":
        return api_testcase_generation_detail(request, task_id)
    return api_testcase_generation_delete(request, task_id)


@login_required
@require_http_methods(["GET"])
def api_testcase_generation_list(request):
    try:
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        status = request.GET.get("status") or None
        qs = TestCaseGenerationTask.objects.filter(created_by=request.user).order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        total = qs.count()
        start = max(0, (page - 1) * page_size)
        items = [_task_to_frontend_payload(t) for t in qs[start:start + page_size]]
        return JsonResponse({"count": total, "results": items})
    except Exception as e:
        logger.error(f"加载任务列表失败: {e}", exc_info=True)
        return _json_error(500, f"加载任务列表失败: {str(e)}", status=500)


@login_required
@require_http_methods(["DELETE"])
def api_testcase_generation_delete(request, task_id: str):
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        task.delete()
        return JsonResponse({"success": True})
    except TestCaseGenerationTask.DoesNotExist:
        return _json_error(404, "任务不存在", status=404)


@login_required
@require_http_methods(["POST"])
def api_testcase_generation_save_to_records(request, task_id: str):
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


# -------------------------------------------------------
# 任务详情页自定义操作接口
# -------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def api_testcase_generation_batch_adopt(request, task_id: str):
    """批量采纳测试用例"""
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
    """批量弃用测试用例"""
    try:
        task = TestCaseGenerationTask.objects.get(task_id=task_id, created_by=request.user)
        data = json.loads(request.body or "{}")
        indices = set(data.get("case_indices", []))
        if not task.final_test_cases:
            return JsonResponse({"discarded_count": 0, "updated_test_cases": ""})
        lines = task.final_test_cases.split("\n")
        header_lines = [l for i, l in enumerate(lines) if i < 2 or not l.strip()]
        data_lines = [l for i, l in enumerate(lines) if i >= 2 and l.strip()]
        kept = [l for i, l in enumerate(data_lines) if i not in indices]
        if not kept:
            task.delete()
            return JsonResponse({"task_deleted": True, "discarded_count": len(indices)})
        updated = "\n".join(header_lines + kept)
        task.final_test_cases = updated
        task.generated_test_cases = updated
        task.save(update_fields=["final_test_cases", "generated_test_cases", "updated_at"])
        return JsonResponse({"discarded_count": len(indices), "updated_test_cases": updated, "task_deleted": False})
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
        header_lines = [l for i, l in enumerate(lines) if i < 2 or not l.strip()]
        data_lines = [l for i, l in enumerate(lines) if i >= 2 and l.strip()]
        if case_index < len(data_lines):
            data_lines.pop(case_index)
        if not data_lines:
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


# -------------------------------------------------------
# AI 模型配置
# -------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def get_ai_models(request):
    try:
        models = AIModelConfig.objects.all()
        data = []
        for m in models:
            data.append({
                "id": m.id, "name": m.name,
                "model_type": m.model_type, "model_type_display": m.get_model_type_display(),
                "role": m.role, "role_display": m.get_role_display(),
                "api_key": m.api_key[:4] + '*' * (len(m.api_key) - 8) + m.api_key[-4:] if m.api_key and len(m.api_key) >= 8 else '',
                "base_url": m.base_url, "model_name": m.model_name,
                "temperature": m.temperature, "max_tokens": m.max_tokens,
                "is_active": m.is_active,
                "created_by": m.created_by.id, "created_by_name": m.created_by.username,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": m.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return JsonResponse({"code": 200, "message": "success", "data": data, "count": len(data), "results": data})
    except Exception as e:
        logger.error(f"获取AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["POST"])
def create_ai_model(request):
    try:
        data = json.loads(request.body)
        name = data.get("name"); model_type = data.get("model_type"); role = data.get("role")
        api_key = data.get("api_key"); base_url = data.get("base_url"); model_name = data.get("model_name")
        if not all([name, model_type, role, api_key, base_url, model_name]):
            return JsonResponse({"code": 400, "message": "请填写所有必填字段"})
        is_active = data.get("is_active", True)
        if is_active:
            AIModelConfig.objects.filter(role=role, is_active=True).update(is_active=False)
        m = AIModelConfig.objects.create(
            name=name, model_type=model_type, role=role, api_key=api_key,
            base_url=base_url, model_name=model_name,
            temperature=data.get("temperature", 0.7), max_tokens=data.get("max_tokens", 4096),
            top_p=data.get("top_p", 0.9), is_active=is_active, created_by=request.user,
        )
        return JsonResponse({"code": 200, "message": "模型配置创建成功", "data": {"id": m.id, "name": m.name}})
    except Exception as e:
        logger.error(f"创建AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def get_ai_model_detail(request, id):
    if request.method in ("PUT", "PATCH"):
        return update_ai_model(request, id)
    if request.method == "DELETE":
        return delete_ai_model(request, id)
    try:
        m = AIModelConfig.objects.get(id=id)
        return JsonResponse({"code": 200, "message": "success", "data": {
            "id": m.id, "name": m.name,
            "model_type": m.model_type, "model_type_display": m.get_model_type_display(),
            "role": m.role, "role_display": m.get_role_display(),
            "api_key": "********" if m.api_key else '',
            "has_api_key": bool(m.api_key),
            "base_url": m.base_url, "model_name": m.model_name,
            "temperature": m.temperature, "max_tokens": m.max_tokens, "top_p": m.top_p,
            "is_active": m.is_active,
            "created_by": m.created_by.id, "created_by_name": m.created_by.username,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": m.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["PUT", "PATCH"])
def update_ai_model(request, id):
    try:
        m = AIModelConfig.objects.get(id=id)
        data = json.loads(request.body)
        if "name" in data: m.name = data["name"]
        if "model_type" in data: m.model_type = data["model_type"]
        if "role" in data: m.role = data["role"]
        if "api_key" in data and data["api_key"] and '*' not in data["api_key"]:
            m.api_key = data["api_key"]
        if "base_url" in data: m.base_url = data["base_url"]
        if "model_name" in data: m.model_name = data["model_name"]
        if "temperature" in data: m.temperature = data["temperature"]
        if "max_tokens" in data: m.max_tokens = data["max_tokens"]
        if "top_p" in data: m.top_p = data["top_p"]
        if "is_active" in data:
            if data["is_active"]:
                AIModelConfig.objects.filter(role=m.role, is_active=True).exclude(id=id).update(is_active=False)
            m.is_active = data["is_active"]
        m.save()
        return JsonResponse({"code": 200, "message": "模型配置更新成功", "data": {"id": m.id, "name": m.name}})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"更新AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["DELETE"])
def delete_ai_model(request, id):
    try:
        AIModelConfig.objects.get(id=id).delete()
        return JsonResponse({"code": 200, "message": "模型配置删除成功"})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["POST"])
def test_ai_model_connection(request, id):
    try:
        m = AIModelConfig.objects.get(id=id)

        async def _ping(config):
            import httpx
            headers = {'Authorization': f'Bearer {config.api_key}', 'Content-Type': 'application/json'}
            base_url = config.base_url.rstrip('/')
            if not base_url.endswith('/chat/completions'):
                url = f"{base_url}/chat/completions" if base_url.endswith('/v1') else f"{base_url}/v1/chat/completions"
            else:
                url = base_url
            data = {
                'model': config.model_name,
                'messages': [{'role': 'user', 'content': 'hi'}],
                'max_tokens': 1,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=data)
                resp.raise_for_status()
                return resp.json()

        asyncio.run(_ping(m))
        return JsonResponse({"code": 200, "message": "连接测试成功", "data": {"success": True}})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"测试AI模型连接失败: {e}")
        return JsonResponse({"code": 500, "message": f"连接测试失败: {str(e)}"})


# -------------------------------------------------------
# 提示词配置
# -------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def get_prompts(request):
    try:
        prompts = PromptConfig.objects.all()
        data = [{"id": p.id, "name": p.name, "prompt_type": p.prompt_type,
                 "prompt_type_display": p.get_prompt_type_display(),
                 "content": p.content, "is_active": p.is_active,
                 "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                 "updated_at": p.updated_at.strftime("%Y-%m-%d %H:%M:%S")} for p in prompts]
        return JsonResponse({"code": 200, "message": "success", "data": data, "count": len(data), "results": data})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["POST"])
def create_prompt(request):
    try:
        data = json.loads(request.body)
        if not data.get("name") or not data.get("prompt_type") or not data.get("content"):
            return JsonResponse({"code": 400, "message": "请填写所有必填字段"})
        is_active = data.get("is_active", True)
        if is_active:
            PromptConfig.objects.filter(prompt_type=data["prompt_type"], is_active=True).update(is_active=False)
        p = PromptConfig.objects.create(
            name=data["name"], prompt_type=data["prompt_type"],
            content=data["content"], is_active=is_active, created_by=request.user,
        )
        return JsonResponse({"code": 200, "message": "提示词配置创建成功", "data": {"id": p.id, "name": p.name}})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def get_prompt_detail(request, id):
    if request.method in ("PUT", "PATCH"):
        return update_prompt(request, id)
    if request.method == "DELETE":
        return delete_prompt(request, id)
    try:
        p = PromptConfig.objects.get(id=id)
        return JsonResponse({"code": 200, "data": {"id": p.id, "name": p.name,
            "prompt_type": p.prompt_type, "content": p.content, "is_active": p.is_active}})
    except PromptConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "提示词配置不存在"})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["PUT", "PATCH"])
def update_prompt(request, id):
    try:
        p = PromptConfig.objects.get(id=id)
        data = json.loads(request.body)
        if "name" in data: p.name = data["name"]
        if "content" in data: p.content = data["content"]
        if "is_active" in data:
            if data["is_active"]:
                PromptConfig.objects.filter(prompt_type=p.prompt_type, is_active=True).exclude(id=id).update(is_active=False)
            p.is_active = data["is_active"]
        p.save()
        return JsonResponse({"code": 200, "message": "提示词配置更新成功"})
    except PromptConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "提示词配置不存在"})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["DELETE"])
def delete_prompt(request, id):
    try:
        PromptConfig.objects.get(id=id).delete()
        return JsonResponse({"code": 200, "message": "提示词配置删除成功"})
    except PromptConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "提示词配置不存在"})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["GET"])
def load_default_prompts(request):
    """加载默认提示词"""
    defaults = [
        {"name": "默认编写提示词", "prompt_type": "writer", "content": "你是一个专业的测试工程师，请根据需求文档生成详细的测试用例，包含测试场景、前置条件、操作步骤、预期结果和优先级。"},
        {"name": "默认评审提示词", "prompt_type": "reviewer", "content": "你是一个资深的测试专家，请对以下测试用例进行评审，检查是否覆盖了所有场景，步骤是否清晰，预期结果是否明确。"},
    ]
    return JsonResponse({"code": 200, "data": defaults})


# -------------------------------------------------------
# 向量模型配置（stub，保持接口可用）
# -------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def get_vector_model_config(request):
    from .models import VectorModelConfig
    cfg = VectorModelConfig.get_config()
    return JsonResponse({"code": 200, "data": {
        "provider": cfg.provider,
        "model": cfg.model,
        "api_key": "********" if cfg.api_key else "",
        "has_api_key": bool(cfg.api_key),
        "api_base": cfg.api_base,
        "dimension": cfg.dimension,
    }})


@login_required
@require_http_methods(["POST"])
def update_vector_model_config(request):
    from .models import VectorModelConfig
    data = json.loads(request.body)
    cfg = VectorModelConfig.get_config()
    if "provider" in data: cfg.provider = data["provider"]
    if "model" in data: cfg.model = data["model"]
    if "api_key" in data and data["api_key"] and "*" not in data["api_key"]:
        cfg.api_key = data["api_key"]
    if "api_base" in data: cfg.api_base = data["api_base"]
    if "dimension" in data: cfg.dimension = data["dimension"]
    cfg.save()
    return JsonResponse({"code": 200, "message": "向量模型配置已更新"})


@login_required
@require_http_methods(["POST"])
def test_vector_model_connection(request):
    return JsonResponse({"code": 200, "message": "连接测试成功", "data": {"success": True}})


# -------------------------------------------------------
# RAG 检索
# -------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def rag_retrieve(request):
    try:
        data = json.loads(request.body)
        query = data.get("query")
        knowledge_base_id = data.get("knowledge_base_id")
        top_k = data.get("top_k", 3)
        if not query:
            return JsonResponse({"code": 400, "message": "查询内容不能为空"})
        results = asyncio.run(RAGService.retrieve_relevant_documents(query, knowledge_base_id, top_k))
        return JsonResponse({"code": 200, "message": "success", "data": results})
    except Exception as e:
        logger.error(f"RAG检索失败: {e}")
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["POST"])
def rag_generate_test_cases(request):
    return JsonResponse({"code": 200, "message": "success", "data": []})


# -------------------------------------------------------
# 旧版 AI 用例接口（兼容路由，简化实现）
# -------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def get_ai_cases(request):
    try:
        qs = TestCaseGenerationTask.objects.filter(created_by=request.user).order_by('-created_at')
        data = [_task_to_frontend_payload(t) for t in qs]
        return JsonResponse({"code": 200, "message": "success", "data": data, "count": len(data), "results": data})
    except Exception as e:
        return JsonResponse({"code": 500, "message": str(e)})


@login_required
@require_http_methods(["POST"])
def create_ai_case(request):
    return JsonResponse({"code": 200, "message": "请使用 /api/testcase-generation/generate/ 接口"})


@login_required
@require_http_methods(["GET"])
def get_ai_case_detail(request, id):
    try:
        task = TestCaseGenerationTask.objects.get(id=id, created_by=request.user)
        return JsonResponse({"code": 200, "data": _task_to_frontend_payload(task)})
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})


@login_required
@require_http_methods(["PUT", "PATCH"])
def update_ai_case(request, id):
    return JsonResponse({"code": 200, "message": "success"})


@login_required
@require_http_methods(["DELETE"])
def delete_ai_case(request, id):
    try:
        TestCaseGenerationTask.objects.get(id=id, created_by=request.user).delete()
        return JsonResponse({"code": 200, "message": "任务删除成功"})
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})


@login_required
@require_http_methods(["POST"])
def run_ai_case(request, id):
    return JsonResponse({"code": 200, "message": "请使用 /api/testcase-generation/generate/ 接口"})


@login_required
@require_http_methods(["GET", "POST"])
def tencent_cloud_config(request):
    """腾讯云配置读写"""
    from .models import TencentCloudConfig
    cfg = TencentCloudConfig.get_config()

    if request.method == "GET":
        return JsonResponse({"code": 200, "data": {
            "secret_id": cfg.secret_id,
            "secret_key": "********" if cfg.secret_key else "",
            "has_secret_key": bool(cfg.secret_key),
            "lke_app_key": "********" if cfg.lke_app_key else "",
            "has_lke_app_key": bool(cfg.lke_app_key),
            "lke_region": cfg.lke_region,
            "updated_at": cfg.updated_at.strftime("%Y-%m-%d %H:%M:%S") if cfg.updated_at else None,
        }})

    data = json.loads(request.body)
    if "secret_id" in data: cfg.secret_id = data["secret_id"]
    if "secret_key" in data and data["secret_key"] and "*" not in data["secret_key"]:
        cfg.secret_key = data["secret_key"]
    if "lke_app_key" in data and data["lke_app_key"] and "*" not in data["lke_app_key"]:
        cfg.lke_app_key = data["lke_app_key"]
    if "lke_region" in data: cfg.lke_region = data["lke_region"]
    cfg.save()
    return JsonResponse({"code": 200, "message": "保存成功"})
