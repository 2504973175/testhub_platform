# -*- coding: utf-8 -*-
"""
腾讯云智能体开发平台（LKE）HTTP SSE 调用服务
文档：https://cloud.tencent.com/document/product/1759/105561
"""

import json
import uuid
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

SSE_URL = "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse"


async def _send_message(client, session_id: str, visitor_biz_id: str, content: str,
                        app_key: str, system_role: Optional[str] = None) -> tuple:
    """发送一条消息并等待完整回复，返回 (回复文本, token统计) 元组"""
    import httpx

    payload = {
        "bot_app_key": app_key,
        "session_id": session_id,
        "visitor_biz_id": visitor_biz_id,
        "request_id": uuid.uuid4().hex,
        "content": content,
        "incremental": False,
        "stream": "enable",
        "workflow_status": "",
        "search_network": "disable",
    }
    if system_role:
        payload["system_role"] = system_role

    final_content = ""
    token_usage = {}

    async with client.stream("POST", SSE_URL, json=payload) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise Exception(f"LKE SSE 请求失败 HTTP {resp.status_code}: {body.decode()}")

        async for line in resp.aiter_lines():
            logger.debug(f"LKE SSE raw: {repr(line)}")
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"LKE SSE JSON解析失败: {repr(raw)}")
                continue

            event_type = data.get("type")

            if event_type == "error":
                err = data.get("error", {})
                raise Exception(f"LKE 智能体错误 {err.get('code')}: {err.get('message')}")

            if event_type == "reply":
                payload_data = data.get("payload", {})
                if payload_data.get("is_from_self"):
                    continue
                c = payload_data.get("content", "")
                if c:
                    final_content = c
                if payload_data.get("is_final"):
                    break

            if event_type == "token_stat":
                payload_data = data.get("payload", {})
                token_usage = {
                    "total_tokens": payload_data.get("token_count", 0),
                    "elapsed_ms": payload_data.get("elapsed", 0),
                    "status": payload_data.get("status_summary", ""),
                }

    logger.info(f"LKE 回复长度: {len(final_content)} token: {token_usage}")
    print(f"[LKE 回复] 长度={len(final_content)} 内容前200字=\n{final_content[:200]}")
    return final_content, token_usage


async def call_lke_agent(content: str, app_key: Optional[str] = None,
                         system_role: Optional[str] = None) -> tuple:
    """
    通过 HTTP SSE 调用腾讯云 LKE 智能体。
    返回 (回复文本, token统计) 元组。
    """
    import httpx

    _app_key = app_key or settings.TENCENT_LKE_APP_KEY
    if not _app_key:
        # 降级读数据库配置
        try:
            from .models import TencentCloudConfig
            cfg = TencentCloudConfig.get_config()
            _app_key = cfg.lke_app_key
        except Exception:
            pass
    if not _app_key:
        raise ValueError("未配置 TENCENT_LKE_APP_KEY")

    session_id = uuid.uuid4().hex[:32]
    visitor_biz_id = uuid.uuid4().hex[:32]

    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"[LKE] session_id={session_id} system_role={repr(system_role[:100] if system_role else None)} content=\n{content[:500]}")
        result, token_usage = await _send_message(client, session_id, visitor_biz_id, content,
                                                  _app_key, system_role=system_role)

    return result, token_usage
