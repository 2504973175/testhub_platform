# -*- coding: utf-8 -*-
import json
import uuid
import asyncio
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import AgentConfig

logger = logging.getLogger(__name__)


def _agent_to_dict(a):
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "bot_app_key": "********" if a.bot_app_key else "",
        "has_key": bool(a.bot_app_key),
        "is_active": a.is_active,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@login_required
@require_http_methods(["GET"])
def list_agents(request):
    agents = AgentConfig.objects.filter(created_by=request.user)
    return JsonResponse({"code": 200, "data": [_agent_to_dict(a) for a in agents]})


@login_required
@require_http_methods(["POST"])
def create_agent(request):
    data = json.loads(request.body)
    if not data.get("name") or not data.get("bot_app_key"):
        return JsonResponse({"code": 400, "message": "name 和 bot_app_key 必填"}, status=400)
    a = AgentConfig.objects.create(
        name=data["name"],
        description=data.get("description", ""),
        bot_app_key=data["bot_app_key"],
        is_active=data.get("is_active", True),
        created_by=request.user,
    )
    return JsonResponse({"code": 200, "data": _agent_to_dict(a)})


@login_required
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def agent_detail(request, pk):
    try:
        a = AgentConfig.objects.get(pk=pk, created_by=request.user)
    except AgentConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "不存在"}, status=404)

    if request.method == "DELETE":
        a.delete()
        return JsonResponse({"code": 200, "message": "已删除"})

    if request.method in ("PUT", "PATCH"):
        data = json.loads(request.body)
        if "name" in data: a.name = data["name"]
        if "description" in data: a.description = data["description"]
        if "bot_app_key" in data and data["bot_app_key"] and "*" not in data["bot_app_key"]:
            a.bot_app_key = data["bot_app_key"]
        if "is_active" in data: a.is_active = data["is_active"]
        a.save()
        return JsonResponse({"code": 200, "data": _agent_to_dict(a)})

    return JsonResponse({"code": 200, "data": _agent_to_dict(a)})


@login_required
@require_http_methods(["POST"])
def agent_chat(request, pk):
    """调用指定智能体对话，返回回复内容"""
    try:
        a = AgentConfig.objects.get(pk=pk, created_by=request.user)
    except AgentConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "智能体不存在"}, status=404)

    data = json.loads(request.body)
    content = data.get("content", "").strip()
    if not content:
        return JsonResponse({"code": 400, "message": "content 不能为空"}, status=400)

    session_id = data.get("session_id") or uuid.uuid4().hex[:32]

    try:
        from .tencent_agent import call_lke_agent
        reply, token_usage = asyncio.run(call_lke_agent(content, app_key=a.bot_app_key))
        return JsonResponse({
            "code": 200,
            "data": {
                "reply": reply,
                "session_id": session_id,
                "token_usage": token_usage,
            }
        })
    except Exception as e:
        logger.error(f"智能体对话失败: {e}", exc_info=True)
        return JsonResponse({"code": 500, "message": str(e)}, status=500)
