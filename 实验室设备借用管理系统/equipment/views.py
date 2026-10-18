from django.shortcuts import render


def index(request):
    """设备管理首页（占位，后续实现设备列表/详情/增删改）"""
    return render(request, 'equipment/index.html')
