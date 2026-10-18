"""
借用流转 API 路由（/api/ 前缀，与页面占位路由 borrow/urls.py 互不影响）
"""
from django.urls import path

from . import api_views

urlpatterns = [
    # 3.1 提交借用申请
    path('borrow/apply', api_views.BorrowApplyView.as_view(), name='borrow_apply'),
    # 3.2 我的申请列表
    path('borrow/my/list', api_views.BorrowMyListView.as_view(), name='borrow_my_list'),
    # 3.3 取消待审批申请
    path('borrow/cancel/<int:recordId>', api_views.BorrowCancelView.as_view(), name='borrow_cancel'),
    # 3.4 待审批列表
    path('admin/borrow/pendingList', api_views.BorrowPendingListView.as_view(), name='borrow_pending_list'),
    # 3.5 审批通过/驳回
    path('admin/borrow/audit/<int:recordId>', api_views.BorrowAuditView.as_view(), name='borrow_audit'),
    # 3.6 全部借用记录总览
    path('admin/borrow/allList', api_views.BorrowAllListView.as_view(), name='borrow_all_list'),
    # 4.1 发起归还申请
    path('borrow/returnApply/<int:recordId>', api_views.BorrowReturnApplyView.as_view(), name='borrow_return_apply'),
    # 4.2 待归还列表
    path('admin/borrow/waitReturnList', api_views.BorrowWaitReturnListView.as_view(), name='borrow_wait_return_list'),
    # 4.3 确认归还
    path('admin/borrow/confirmReturn/<int:recordId>', api_views.BorrowConfirmReturnView.as_view(), name='borrow_confirm_return'),
    # 5.1 设备借用统计 / 5.2 用户借用统计
    path('admin/statistics/equipment', api_views.EquipmentStatisticsView.as_view(), name='statistics_equipment'),
    path('admin/statistics/user', api_views.UserStatisticsView.as_view(), name='statistics_user'),
    # 5.4 导出借用记录 Excel
    path('admin/export/borrowRecord', api_views.BorrowExportView.as_view(), name='export_borrow_record'),
]
