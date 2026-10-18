"""
借用流转序列化器（开发者 B）

包含：借用申请（3.1）、我的申请列表查询（3.2）、审批（3.5）、
全部记录查询（3.6）、确认归还（4.3）、导出查询（5.4）等接口的请求/查询参数校验。

本层只负责"不依赖数据库表"的校验 —— 字段完整性、枚举取值、时间规则，
依赖 user / equipment / borrow_records 表的业务校验在 borrow.services 中实现，
G2 表结构会签后补全。
"""
from django.utils import timezone
from rest_framework import serializers

from common.enums import AuditResult, BorrowApprovalStatus, OverdueStatus, ReturnType

from .models import BorrowRecord


class BorrowApplySerializer(serializers.Serializer):
    equipmentId = serializers.IntegerField(
        label='设备ID',
        min_value=1,
        error_messages={'required': '设备ID不能为空', 'min_value': '设备ID不合法'},
    )
    planBorrowStart = serializers.DateTimeField(
        label='计划借用开始时间',
        input_formats=['%Y-%m-%d %H:%M:%S'],
        error_messages={'required': '借用开始时间不能为空', 'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )
    planReturnTime = serializers.DateTimeField(
        label='计划归还时间',
        input_formats=['%Y-%m-%d %H:%M:%S'],
        error_messages={'required': '计划归还时间不能为空', 'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )
    borrowPurpose = serializers.CharField(
        label='借用用途',
        max_length=200,
        error_messages={'required': '借用用途不能为空', 'max_length': '借用用途不能超过200字'},
    )
    remark = serializers.CharField(
        label='备注',
        required=False,
        allow_blank=True,
        max_length=500,
        error_messages={'max_length': '备注不能超过500字'},
    )

    def validate(self, attrs):
        now = timezone.now()
        start = attrs['planBorrowStart']
        end = attrs['planReturnTime']

        # 校验 2-a：开始时间不能早于当前时间
        if start < now:
            raise serializers.ValidationError('借用开始时间不能早于当前时间')

        # 校验 2-b：归还时间必须晚于开始时间
        if end <= start:
            raise serializers.ValidationError('计划归还时间必须晚于借用开始时间')

        return attrs


class BorrowMyListQuerySerializer(serializers.Serializer):
    """3.2 我的申请列表查询参数（GET /api/borrow/my/list）"""
    approvalStatus = serializers.ChoiceField(
        choices=BorrowApprovalStatus.choices,
        required=False,
        label='审批状态',
        error_messages={'invalid_choice': '审批状态取值不合法'},
    )


class BorrowAllListQuerySerializer(serializers.Serializer):
    """3.6 全部借用记录总览查询参数（GET /api/admin/borrow/allList）"""
    userId = serializers.IntegerField(required=False, min_value=1, label='用户ID')
    equipmentId = serializers.IntegerField(required=False, min_value=1, label='设备ID')
    startTime = serializers.DateTimeField(
        required=False, input_formats=['%Y-%m-%d %H:%M:%S'], label='开始时间',
        error_messages={'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )
    endTime = serializers.DateTimeField(
        required=False, input_formats=['%Y-%m-%d %H:%M:%S'], label='结束时间',
        error_messages={'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )
    overdueStatus = serializers.ChoiceField(
        choices=OverdueStatus.choices, required=False, label='逾期状态',
        error_messages={'invalid_choice': '逾期状态取值不合法'},
    )


class BorrowAuditSerializer(serializers.Serializer):
    """3.5 审批通过/驳回（PUT /api/admin/borrow/audit/{recordId}）"""
    result = serializers.ChoiceField(
        choices=AuditResult.choices,
        label='审批结果',
        error_messages={'required': '审批结果不能为空', 'invalid_choice': '审批结果只能是 pass 或 reject'},
    )
    opinion = serializers.CharField(
        label='审批意见',
        required=False,
        allow_blank=True,
        max_length=500,
        error_messages={'max_length': '审批意见不能超过500字'},
    )

    def validate(self, attrs):
        if attrs['result'] == AuditResult.REJECT and not attrs.get('opinion', '').strip():
            raise serializers.ValidationError('驳回时必须填写审批意见')
        return attrs


class ReturnConfirmSerializer(serializers.Serializer):
    """4.3 确认归还（PUT /api/admin/borrow/confirmReturn/{recordId}）"""
    returnType = serializers.ChoiceField(
        choices=ReturnType.choices,
        label='归还结果',
        error_messages={'required': '归还结果不能为空', 'invalid_choice': '归还结果只能是 normal/damage/lose'},
    )
    remark = serializers.CharField(
        label='归还说明',
        required=False,
        allow_blank=True,
        max_length=500,
        error_messages={'max_length': '归还说明不能超过500字'},
    )


class BorrowExportQuerySerializer(serializers.Serializer):
    """5.4 导出借用记录 Excel 查询参数（GET /api/admin/export/borrowRecord）"""
    startTime = serializers.DateTimeField(
        required=False, input_formats=['%Y-%m-%d %H:%M:%S'], label='开始时间',
        error_messages={'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )
    endTime = serializers.DateTimeField(
        required=False, input_formats=['%Y-%m-%d %H:%M:%S'], label='结束时间',
        error_messages={'invalid': '时间格式应为 yyyy-MM-dd HH:mm:ss'},
    )


# ============================================================
# 输出序列化器（读 borrow_record 表，表已迁移可用）
# ============================================================

class BorrowRecordSerializer(serializers.ModelSerializer):
    """借用记录输出（列表/详情通用），字段转 camelCase，时间统一 yyyy-MM-dd HH:mm:ss"""

    userId = serializers.IntegerField(source='user_id', read_only=True)
    equipmentId = serializers.IntegerField(source='equipment_id', read_only=True)
    planBorrowStart = serializers.DateTimeField(source='plan_borrow_start', read_only=True)
    planReturnTime = serializers.DateTimeField(source='plan_return_time', read_only=True)
    borrowPurpose = serializers.CharField(source='borrow_purpose', read_only=True)
    approvalStatus = serializers.CharField(source='approval_status', read_only=True)
    overdueStatus = serializers.CharField(source='overdue_status', read_only=True)
    auditOpinion = serializers.CharField(source='audit_opinion', read_only=True)
    auditTime = serializers.DateTimeField(source='audit_time', read_only=True)
    cancelTime = serializers.DateTimeField(source='cancel_time', read_only=True)
    returnApplyTime = serializers.DateTimeField(source='return_apply_time', read_only=True)
    actualReturnTime = serializers.DateTimeField(source='actual_return_time', read_only=True)
    returnType = serializers.CharField(source='return_type', read_only=True)
    createTime = serializers.DateTimeField(source='create_time', read_only=True)
    updateTime = serializers.DateTimeField(source='update_time', read_only=True)

    class Meta:
        model = BorrowRecord
        fields = [
            'id', 'userId', 'equipmentId', 'planBorrowStart', 'planReturnTime',
            'borrowPurpose', 'remark', 'approvalStatus', 'overdueStatus', 'auditOpinion',
            'auditTime', 'cancelTime', 'returnApplyTime', 'actualReturnTime', 'returnType',
            'createTime', 'updateTime',
        ]
