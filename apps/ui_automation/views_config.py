from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import shutil
import subprocess
import platform
import os
import json

class EnvironmentConfigViewSet(viewsets.ViewSet):
    """
    UI自动化环境配置视图集
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def check_environment(self, request):
        """
        检测环境状态 (系统浏览器和Playwright浏览器)
        """
        import sys
        
        # 1. 检测系统浏览器 (Selenium常用)
        system_browsers_list = ['chrome', 'firefox', 'edge'] # Safari not on Windows usually
        if platform.system() == 'Darwin':
             system_browsers_list.append('safari')
             
        system_results = []

        is_windows = platform.system() == 'Windows'

        for browser in system_browsers_list:
            installed = False
            version = None
            install_cmd = ""
            
            if browser == 'chrome':
                if is_windows:
                    paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            installed = True
                            break
                    install_cmd = "请下载 Chrome 安装包安装"
                else: # macOS
                    if os.path.exists('/Applications/Google Chrome.app'):
                        installed = True
                    install_cmd = "brew install --cask google-chrome"
                    
            elif browser == 'firefox':
                if is_windows:
                    paths = [
                        r"C:\Program Files\Mozilla Firefox\firefox.exe",
                        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            installed = True
                            break
                    install_cmd = "请下载 Firefox 安装包安装"
                else:
                    if os.path.exists('/Applications/Firefox.app'):
                        installed = True
                    install_cmd = "brew install --cask firefox"
                    
            elif browser == 'safari':
                if not is_windows and os.path.exists('/Applications/Safari.app'):
                    installed = True
                install_cmd = "系统自带"
                
            elif browser == 'edge':
                if is_windows:
                    paths = [
                         r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                    ]
                    for p in paths:
                        if os.path.exists(p):
                            installed = True
                            break
                    install_cmd = "请下载 Edge 安装包安装"
                else:
                    if os.path.exists('/Applications/Microsoft Edge.app'):
                        installed = True
                    install_cmd = "brew install --cask microsoft-edge"

            system_results.append({
                'name': browser,
                'installed': installed,
                'version': version, # Version check omitted for simplicity/performance
                'install_cmd': install_cmd
            })

        # 2. 检测Playwright浏览器
        playwright_browsers_list = ['chromium', 'firefox', 'webkit']
        playwright_results = []
        
        # Playwright 缓存路径
        if is_windows:
            playwright_cache_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'ms-playwright')
        else:
            playwright_cache_dir = os.path.expanduser('~/Library/Caches/ms-playwright')
        
        # 调试信息：打印缓存路径
        print(f"Playwright cache dir: {playwright_cache_dir}")

        for browser in playwright_browsers_list:
            installed = False
            version = None
            install_cmd = f"playwright install {browser}"
            
            # 检查缓存目录中是否有对应的浏览器文件夹
            if os.path.exists(playwright_cache_dir):
                for dirname in os.listdir(playwright_cache_dir):
                    # 匹配规则: chromium-123456, firefox-1234, webkit-1234
                    # 注意: 有时候是 chromium-vxxxx
                    if dirname.startswith(browser + '-'):
                        installed = True
                        version = dirname.split('-')[-1]
                        break
            
            playwright_results.append({
                'name': browser,
                'installed': installed,
                'version': version,
                'install_cmd': install_cmd
            })

        return Response({
            'os': platform.system(),
            'system_browsers': system_results,
            'playwright_browsers': playwright_results
        })

    @action(detail=False, methods=['post'])
    def install_driver(self, request):
        """
        安装浏览器驱动
        """
        browser = request.data.get('browser')
        if not browser:
            return Response({'error': 'Browser name is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 使用当前 Python 环境执行模块安装命令
            import sys
            subprocess.run([sys.executable, '-m', 'playwright', 'install', browser], check=True)
            return Response({'message': f'Successfully installed driver for {browser}'})
        except subprocess.CalledProcessError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import requests
from apps.requirement_analysis.models import AIModelConfig

class AIIntelligentModeConfigViewSet(viewsets.ViewSet):
    """
    AI智能模式配置视图集 (Browser-use)
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        获取当前配置
        """
        # 获取文本模式配置
        text_config = AIModelConfig.get_active_config(
            model_type='other', # 这里主要通过role来区分，model_type可能会变，但role是关键
            role='browser_use_text'
        )
        
        if not text_config:
            text_config = AIModelConfig.objects.filter(role='browser_use_text', is_active=True).first()
        
        # 默认配置结构 (仅包含文本模式)
        response_data = {
            'text_model': {
                'provider': text_config.model_type if text_config else 'openai',
                'model_name': text_config.model_name if text_config else 'gpt-4o',
                'api_key': text_config.api_key if text_config else '',
                'base_url': text_config.base_url if text_config else ''
            }
        }
        
        return Response(response_data)

    def create(self, request):
        """
        保存配置
        """
        config = request.data
        text_model_data = config.get('text_model', {})
        
        user = request.user
        
        # 保存文本模式配置
        if text_model_data:
            AIModelConfig.objects.update_or_create(
                role='browser_use_text',
                defaults={
                    'name': 'Browser Use Text Model',
                    'model_type': text_model_data.get('provider', 'other'),
                    'model_name': text_model_data.get('model_name', ''),
                    'api_key': text_model_data.get('api_key', ''),
                    'base_url': text_model_data.get('base_url', ''),
                    'is_active': True,
                    'created_by': user
                }
            )
            

            
        return Response(config)

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """
        测试模型连接
        """
        provider = request.data.get('provider')
        base_url = request.data.get('base_url')
        api_key = request.data.get('api_key')
        model_name = request.data.get('model_name')
        
        if not api_key:
            return Response({'error': 'API Key is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 默认Base URL处理
        if not base_url:
            if provider == 'openai':
                base_url = 'https://api.openai.com/v1'
            elif provider == 'siliconflow':
                base_url = 'https://api.siliconflow.cn/v1'
            elif provider == 'deepseek':
                base_url = 'https://api.deepseek.com'
            elif provider == 'google_gemini':
                # Gemini usually requires specific library or different endpoint structure
                # For now, assuming OpenAI compatible endpoint if base_url is provided, 
                # or we might need special handling.
                pass
        
        if not base_url:
             return Response({'error': 'Base URL is required for this provider'}, status=status.HTTP_400_BAD_REQUEST)

        base_url = base_url.rstrip('/')
        
        try:
            # 尝试调用 chat completions 接口 (OpenAI Compatible)
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                return Response({'message': '连接成功'})
            else:
                return Response({'error': f'连接失败: {response.status_code} - {response.text}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'连接异常: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
