# -*- coding: utf-8 -*-
"""
腾讯云配置读取工具
优先级：数据库配置 > .env 配置
"""
from django.conf import settings


def get_tencent_config() -> dict:
    """获取腾讯云配置，数据库优先，.env 兜底"""
    result = {
        "secret_id": settings.TENCENT_SECRET_ID,
        "secret_key": settings.TENCENT_SECRET_KEY,
        "lke_app_key": settings.TENCENT_LKE_APP_KEY,
        "lke_region": settings.TENCENT_LKE_REGION,
    }
    try:
        from .models import TencentCloudConfig
        cfg = TencentCloudConfig.get_config()
        if cfg.secret_id:   result["secret_id"]   = cfg.secret_id
        if cfg.secret_key:  result["secret_key"]  = cfg.secret_key
        if cfg.lke_app_key: result["lke_app_key"] = cfg.lke_app_key
        if cfg.lke_region:  result["lke_region"]  = cfg.lke_region
    except Exception:
        pass
    return result
