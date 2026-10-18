from django.shortcuts import render


def index(request):
    """借用管理首页（占位，后续实现借用申请/审批/归还）"""
    return render(request, 'borrow/index.html')
