# -*- coding: utf-8 -*-
"""
需求分析模块视图
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import UploadedFile
import json
import logging
import asyncio

from .models import TestCaseGenerationTask, AIModelConfig
from .ai_models import AIModelService
from .rag_services import RAGService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def get_ai_cases(request):
    """获取AI用例列表"""
    try:
        # 这里应该实现获取AI用例列表的逻辑
        # 暂时返回模拟数据
        ai_cases = [
            {
                "id": 1,
                "name": "用户登录测试",
                "description": "测试用户登录功能",
                "task_description": "测试用户使用有效凭证登录系统",
                "created_at": "2024-01-01 10:00:00",
                "created_by": "admin"
            },
            {
                "id": 2,
                "name": "数据录入测试",
                "description": "测试数据录入功能",
                "task_description": "测试数据录入和验证功能",
                "created_at": "2024-01-02 14:30:00",
                "created_by": "admin"
            }
        ]
        return JsonResponse({"code": 200, "message": "success", "data": ai_cases})
    except Exception as e:
        logger.error(f"获取AI用例列表失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI用例列表失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def create_ai_case(request):
    """创建AI用例"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        description = data.get("description")
        task_description = data.get("task_description")
        
        if not name or not task_description:
            return JsonResponse({"code": 400, "message": "用例名称和任务描述不能为空"})
        
        # 这里应该实现创建AI用例的逻辑
        # 暂时返回模拟数据
        ai_case = {
            "id": 3,
            "name": name,
            "description": description,
            "task_description": task_description,
            "created_at": "2024-01-03 09:00:00",
            "created_by": request.user.username
        }
        return JsonResponse({"code": 200, "message": "success", "data": ai_case})
    except Exception as e:
        logger.error(f"创建AI用例失败: {e}")
        return JsonResponse({"code": 500, "message": f"创建AI用例失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def get_ai_case_detail(request, id):
    """获取AI用例详情"""
    try:
        # 这里应该实现获取AI用例详情的逻辑
        # 暂时返回模拟数据
        ai_case = {
            "id": id,
            "name": "用户登录测试",
            "description": "测试用户登录功能",
            "task_description": "测试用户使用有效凭证登录系统",
            "created_at": "2024-01-01 10:00:00",
            "created_by": "admin"
        }
        return JsonResponse({"code": 200, "message": "success", "data": ai_case})
    except Exception as e:
        logger.error(f"获取AI用例详情失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI用例详情失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def update_ai_case(request, id):
    """更新AI用例"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        description = data.get("description")
        task_description = data.get("task_description")
        
        # 这里应该实现更新AI用例的逻辑
        # 暂时返回成功消息
        return JsonResponse({"code": 200, "message": "success"})
    except Exception as e:
        logger.error(f"更新AI用例失败: {e}")
        return JsonResponse({"code": 500, "message": f"更新AI用例失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def delete_ai_case(request, id):
    """删除AI用例"""
    try:
        # 这里应该实现删除AI用例的逻辑
        # 暂时返回成功消息
        return JsonResponse({"code": 200, "message": "success"})
    except Exception as e:
        logger.error(f"删除AI用例失败: {e}")
        return JsonResponse({"code": 500, "message": f"删除AI用例失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def run_ai_case(request, id):
    """运行AI用例"""
    try:
        # 这里应该实现运行AI用例的逻辑
        # 暂时返回模拟数据
        execution_result = {
            "id": 1,
            "case_id": id,
            "status": "running",
            "start_time": "2024-01-03 10:00:00",
            "logs": "开始执行测试用例..."
        }
        return JsonResponse({"code": 200, "message": "success", "data": execution_result})
    except Exception as e:
        logger.error(f"运行AI用例失败: {e}")
        return JsonResponse({"code": 500, "message": f"运行AI用例失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def rag_retrieve(request):
    """RAG检索"""
    try:
        data = json.loads(request.body)
        query = data.get("query")
        knowledge_base_id = data.get("knowledge_base_id")
        top_k = data.get("top_k", 5)
        
        if not query or not knowledge_base_id:
            return JsonResponse({"code": 400, "message": "查询内容和知识库ID不能为空"})
        
        # 异步调用RAG检索
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        relevant_chunks = loop.run_until_complete(
            RAGService.retrieve_relevant_documents(query, knowledge_base_id, top_k)
        )
        loop.close()
        
        return JsonResponse({"code": 200, "message": "success", "data": relevant_chunks})
    except Exception as e:
        logger.error(f"RAG检索失败: {e}")
        return JsonResponse({"code": 500, "message": f"RAG检索失败: {str(e)}"})


@login_required
@require_http_methods(["POST"])
def rag_generate_test_cases(request):
    """使用RAG生成测试用例"""
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        knowledge_base_id = data.get("knowledge_base_id")
        
        if not task_id or not knowledge_base_id:
            return JsonResponse({"code": 400, "message": "任务ID和知识库ID不能为空"})
        
        # 获取任务
        task = TestCaseGenerationTask.objects.get(task_id=task_id)
        
        # 异步调用AI生成测试用例
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        test_cases = loop.run_until_complete(
            AIModelService.generate_test_cases(task, knowledge_base_id)
        )
        loop.close()
        
        # 更新任务结果
        task.generated_test_cases = test_cases
        task.status = "completed"
        task.progress = 100
        task.save()
        
        return JsonResponse({"code": 200, "message": "success", "data": test_cases})
    except TestCaseGenerationTask.DoesNotExist:
        return JsonResponse({"code": 404, "message": "任务不存在"})
    except Exception as e:
        logger.error(f"生成测试用例失败: {e}")
        return JsonResponse({"code": 500, "message": f"生成测试用例失败: {str(e)}"})


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
                "base_url": model.base_url,
                "model_name": model.model_name,
                "max_tokens": model.max_tokens,
                "temperature": model.temperature,
                "top_p": model.top_p,
                "is_active": model.is_active,
                "api_key_masked": "*" * len(model.api_key) if model.api_key else "",
                "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S")
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
        max_tokens = data.get("max_tokens", 4096)
        temperature = data.get("temperature", 0.7)
        top_p = data.get("top_p", 0.9)
        is_active = data.get("is_active", True)
        
        if not name or not model_type or not role or not api_key or not base_url or not model_name:
            return JsonResponse({"code": 400, "message": "缺少必填字段"})
        
        # 检查是否已存在相同角色的活跃配置
        if is_active:
            existing = AIModelConfig.objects.filter(model_type=model_type, role=role, is_active=True).first()
            if existing:
                return JsonResponse({"code": 400, "message": f"已存在相同角色的活跃配置: {existing.name}"})
        
        model = AIModelConfig.objects.create(
            name=name,
            model_type=model_type,
            role=role,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            is_active=is_active,
            created_by=request.user
        )
        
        return JsonResponse({"code": 200, "message": "success", "data": {
            "id": model.id,
            "name": model.name,
            "model_type": model.model_type,
            "model_type_display": model.get_model_type_display(),
            "role": model.role,
            "role_display": model.get_role_display(),
            "base_url": model.base_url,
            "model_name": model.model_name,
            "max_tokens": model.max_tokens,
            "temperature": model.temperature,
            "top_p": model.top_p,
            "is_active": model.is_active,
            "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }})
    except Exception as e:
        logger.error(f"创建AI模型配置失败: {e}")
        return JsonResponse({"code": 500, "message": f"创建AI模型配置失败: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def get_ai_model_detail(request, id):
    """获取AI模型配置详情"""
    try:
        model = AIModelConfig.objects.get(id=id)
        data = {
            "id": model.id,
            "name": model.name,
            "model_type": model.model_type,
            "model_type_display": model.get_model_type_display(),
            "role": model.role,
            "role_display": model.get_role_display(),
            "base_url": model.base_url,
            "model_name": model.model_name,
            "max_tokens": model.max_tokens,
            "temperature": model.temperature,
            "top_p": model.top_p,
            "is_active": model.is_active,
            "api_key_masked": "*" * len(model.api_key) if model.api_key else "",
            "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        return JsonResponse({"code": 200, "message": "success", "data": data})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"获取AI模型配置详情失败: {e}")
        return JsonResponse({"code": 500, "message": f"获取AI模型配置详情失败: {str(e)}"})


@login_required
@require_http_methods(["PATCH"])
def update_ai_model(request, id):
    """更新AI模型配置"""
    try:
        data = json.loads(request.body)
        model = AIModelConfig.objects.get(id=id)
        
        # 更新字段
        if "name" in data:
            model.name = data["name"]
        if "model_type" in data:
            model.model_type = data["model_type"]
        if "role" in data:
            model.role = data["role"]
        if "api_key" in data and data["api_key"]:
            model.api_key = data["api_key"]
        if "base_url" in data:
            model.base_url = data["base_url"]
        if "model_name" in data:
            model.model_name = data["model_name"]
        if "max_tokens" in data:
            model.max_tokens = data["max_tokens"]
        if "temperature" in data:
            model.temperature = data["temperature"]
        if "top_p" in data:
            model.top_p = data["top_p"]
        if "is_active" in data:
            model.is_active = data["is_active"]
            # 检查是否已存在相同角色的活跃配置
            if model.is_active:
                existing = AIModelConfig.objects.filter(model_type=model.model_type, role=model.role, is_active=True).exclude(id=id).first()
                if existing:
                    return JsonResponse({"code": 400, "message": f"已存在相同角色的活跃配置: {existing.name}"})
        
        model.save()
        
        return JsonResponse({"code": 200, "message": "success", "data": {
            "id": model.id,
            "name": model.name,
            "model_type": model.model_type,
            "model_type_display": model.get_model_type_display(),
            "role": model.role,
            "role_display": model.get_role_display(),
            "base_url": model.base_url,
            "model_name": model.model_name,
            "max_tokens": model.max_tokens,
            "temperature": model.temperature,
            "top_p": model.top_p,
            "is_active": model.is_active,
            "created_at": model.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }})
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
        return JsonResponse({"code": 200, "message": "success"})
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
        
        # 测试连接
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 构造测试消息
        test_messages = [
            {"role": "system", "content": "你是一个测试助手，只需要回复'测试成功'"},
            {"role": "user", "content": "请回复'测试成功'"}
        ]
        
        response = loop.run_until_complete(
            AIModelService.call_openai_compatible_api(model, test_messages)
        )
        loop.close()
        
        # 提取响应内容
        response_content = response['choices'][0]['message']['content']
        
        return JsonResponse({"code": 200, "message": "success", "data": {
            "success": True,
            "message": "连接测试成功",
            "response": response_content
        }})
    except AIModelConfig.DoesNotExist:
        return JsonResponse({"code": 404, "message": "模型配置不存在"})
    except Exception as e:
        logger.error(f"测试AI模型连接失败: {e}")
        return JsonResponse({"code": 200, "message": "success", "data": {
            "success": False,
            "message": f"连接测试失败: {str(e)}",
            "response": ""
        }})
