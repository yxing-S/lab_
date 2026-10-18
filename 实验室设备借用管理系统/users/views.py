from django.shortcuts import render


def index(request):
    """用户中心首页（占位，后续实现登录/资料/角色权限）"""
    return render(request, 'users/index.html')
