"""
借用流转 API 视图（开发者 B）

分层：serializer（无表校验）-> services（业务/事务）-> 标准返回。
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.audit import log_operation
from common.enums import LogModule
from common.excel import write_excel_response
from common.pagination import StandardResultsSetPagination
from common.permissions import IsAdmin
from common.response import ok
from . import services
from .serializers import (
    BorrowAllListQuerySerializer,
    BorrowApplySerializer,
    BorrowAuditSerializer,
    BorrowExportQuerySerializer,
    BorrowMyListQuerySerializer,
    BorrowRecordSerializer,
    ReturnConfirmSerializer,
)

# 导出条数上限（与分页上限一致，见 5.3 / 5.4 约束）
_EXPORT_MAX = StandardResultsSetPagination.max_page_size


# ============================================================
# 3.1 提交借用申请
# ============================================================

@log_operation(module=LogModule.BORROW, action='提交借用申请')
class BorrowApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BorrowApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.apply_borrow(request.user, serializer.validated_data)
        return ok({'id': record.id}, '借用申请提交成功')


# ============================================================
# 3.2 我的申请列表
# ============================================================

class BorrowMyListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        params = BorrowMyListQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return services.query_my_borrow(
            self.request.user.id,
            params.validated_data.get('approvalStatus'),
        )


# ============================================================
# 3.3 取消待审批申请
# ============================================================

@log_operation(module=LogModule.BORROW, action='取消借用申请')
class BorrowCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, recordId):
        services.cancel_borrow(request.user.id, recordId)
        return ok(msg='借用申请已取消')


# ============================================================
# 3.4 待审批列表 / 3.5 审批 / 3.6 全部记录
# ============================================================

class BorrowPendingListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        return services.query_pending_borrow()


@log_operation(module=LogModule.BORROW, action='审批借用申请')
class BorrowAuditView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, recordId):
        serializer = BorrowAuditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.audit_borrow(
            recordId,
            serializer.validated_data['result'],
            serializer.validated_data.get('opinion', ''),
        )
        return ok({'id': record.id, 'approvalStatus': record.approval_status}, '审批完成')


class BorrowAllListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        params = BorrowAllListQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        d = params.validated_data
        return services.query_all_borrow(
            d.get('userId'),
            d.get('equipmentId'),
            d.get('startTime'),
            d.get('endTime'),
            d.get('overdueStatus'),
        )


# ============================================================
# 4.1 发起归还 / 4.2 待归还列表 / 4.3 确认归还
# ============================================================

@log_operation(module=LogModule.RETURN, action='发起归还申请')
class BorrowReturnApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, recordId):
        services.apply_return(request.user.id, recordId)
        return ok(msg='归还申请已提交')


class BorrowWaitReturnListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        return services.query_wait_return()


@log_operation(module=LogModule.RETURN, action='确认归还')
class BorrowConfirmReturnView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, recordId):
        serializer = ReturnConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = services.confirm_return(
            recordId,
            serializer.validated_data['returnType'],
            serializer.validated_data.get('remark', ''),
        )
        return ok({'id': record.id, 'overdueStatus': record.overdue_status}, '归还确认完成')


# ============================================================
# 5.1 / 5.2 统计
# ============================================================

class EquipmentStatisticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return ok(services.equipment_statistics())


class UserStatisticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return ok(services.user_statistics())


# ============================================================
# 5.4 导出借用记录 Excel
# ============================================================

class BorrowExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        params = BorrowExportQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        records = services.query_export_borrow(
            params.validated_data.get('startTime'),
            params.validated_data.get('endTime'),
        )[:_EXPORT_MAX]

        headers = ['记录ID', '用户ID', '设备ID', '计划借用开始', '计划归还', '借用用途',
                   '审批状态', '逾期状态', '实际归还时间', '归还类型', '创建时间']
        rows = [
            [r.id, r.user_id, r.equipment_id,
             r.plan_borrow_start.strftime('%Y-%m-%d %H:%M:%S'),
             r.plan_return_time.strftime('%Y-%m-%d %H:%M:%S'),
             r.borrow_purpose, r.approval_status, r.overdue_status,
             r.actual_return_time.strftime('%Y-%m-%d %H:%M:%S') if r.actual_return_time else '',
             r.return_type or '', r.create_time.strftime('%Y-%m-%d %H:%M:%S')]
            for r in records
        ]
        return write_excel_response('借用记录', headers, rows)
