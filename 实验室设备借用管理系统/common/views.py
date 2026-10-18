"""
通用字典接口（G11，接口文档第 7 节）

7.1 GET /api/dict/equipmentStatus  -> 设备状态
7.2 GET /api/dict/borrowStatus     -> 借用审批状态
登录用户（admin/user）均可访问。
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .enums import BORROW_STATUS_DICT, EQUIPMENT_STATUS_DICT
from .models import OperationLog
from .pagination import StandardResultsSetPagination
from .permissions import IsAdmin
from .serializers import OperationLogQuerySerializer, OperationLogSerializer


class EquipmentStatusDictView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework.response import Response
        return Response(EQUIPMENT_STATUS_DICT)


class BorrowStatusDictView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework.response import Response
        return Response(BORROW_STATUS_DICT)


class OperationLogListView(generics.ListAPIView):
    """6.1 操作日志查询（GET /api/admin/log/list，仅管理员）"""

    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination
    serializer_class = OperationLogSerializer

    def get_queryset(self):
        params = OperationLogQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        d = params.validated_data

        qs = OperationLog.objects.all()
        if d.get('module'):
            qs = qs.filter(module=d['module'])
        if d.get('operatorId'):
            qs = qs.filter(operator_id=d['operatorId'])
        if d.get('startTime'):
            qs = qs.filter(create_time__gte=d['startTime'])
        if d.get('endTime'):
            qs = qs.filter(create_time__lte=d['endTime'])
        return qs.order_by('-create_time')
