"""通用字典路由（G11）"""
from django.urls import path

from . import views

app_name = 'common'

urlpatterns = [
    path('dict/equipmentStatus', views.EquipmentStatusDictView.as_view(), name='equipment_status_dict'),
    path('dict/borrowStatus', views.BorrowStatusDictView.as_view(), name='borrow_status_dict'),
    path('admin/log/list', views.OperationLogListView.as_view(), name='operation_log_list'),
]
