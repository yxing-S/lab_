"""
操作日志查询序列化器（6.1 GET /api/admin/log/list，开发者 B）

本层只做查询参数校验，不依赖数据库表；6.1 视图与 OperationLog 查询逻辑
在 G2 会签并完成 operation_log 迁移后补齐。
"""
from rest_framework import serializers

from .enums import LogModule
from .models import OperationLog


class OperationLogQuerySerializer(serializers.Serializer):
    """6.1 操作日志查询参数（page/size 由分页组件处理，此处不含）"""
    module = serializers.ChoiceField(
        choices=LogModule.choices, required=False, label='功能模块',
        error_messages={'invalid_choice': '模块取值不合法'},
    )
    operatorId = serializers.IntegerField(required=False, min_value=1, label='操作人ID')
    startTime = serializers.DateTimeField(
        required=False, input_formats=['%Y-%m-%d %H:%M:%S'], label='开始时间',
        error_messages={'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )
    endTime = serializers.DateTimeField(
        required=False, input_formats=['%Y-%m-%d %H:%M:%S'], label='结束时间',
        error_messages={'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )


class OperationLogSerializer(serializers.ModelSerializer):
    """6.1 操作日志输出（字段转 camelCase，时间统一 yyyy-MM-dd HH:mm:ss）"""

    operatorId = serializers.IntegerField(source='operator_id', read_only=True, allow_null=True)
    operatorName = serializers.CharField(source='operator_name', read_only=True)
    statusCode = serializers.IntegerField(source='status_code', read_only=True)
    createTime = serializers.DateTimeField(source='create_time', read_only=True)

    class Meta:
        model = OperationLog
        fields = [
            'id', 'operatorId', 'operatorName', 'module', 'action', 'method',
            'path', 'params', 'ip', 'success', 'statusCode', 'createTime',
        ]
