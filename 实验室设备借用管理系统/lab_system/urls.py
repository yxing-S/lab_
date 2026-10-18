"""
URL configuration for lab_system project.
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    # 系统首页（占位页面，与 /api/ 接口互不影响）
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    # API：公共字典（G11，B）
    path('api/', include('common.urls')),
    # API：借用流转（B，3.1 起；其余待 G2 会签后补）
    path('api/', include('borrow.api_urls')),
    # 各业务应用
    path('users/', include('users.urls')),
    path('equipment/', include('equipment.urls')),
    path('borrow/', include('borrow.urls')),
]
