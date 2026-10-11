"""设备模块 Serializer（接口文档 2.1 - 2.6 / 5.3，责任人 A）"""
from decimal import Decimal

from rest_framework import serializers

from apps.common.constants import EquipmentStatus
from apps.equipment.models import Equipment


# ================= 请求 Serializer =================

class EquipmentAddSerializer(serializers.ModelSerializer):
    """2.3 管理员新增设备"""

    equipmentNo = serializers.CharField(source="equipment_no", max_length=50)
    buyDate = serializers.DateField(source="buy_date", required=False, allow_null=True)
    imgUrl = serializers.CharField(source="img_url", max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=EquipmentStatus.ALL, default=EquipmentStatus.IDLE
    )

    class Meta:
        model = Equipment
        fields = ["equipmentNo", "name", "model", "spec", "buyDate",
                  "price", "location", "status", "imgUrl", "remark"]
        extra_kwargs = {
            "name": {"max_length": 100},
            "model": {"max_length": 100, "required": False},
            "spec": {"max_length": 200, "required": False},
            "location": {"max_length": 200, "required": False},
            "remark": {"max_length": 500, "required": False},
        }


class EquipmentUpdateSerializer(serializers.ModelSerializer):
    """2.4 管理员编辑设备

    业务约束（后端强制）：设备处于"借出中"时禁止手动改 status；
    也禁止通过编辑接口把设备改为"借出中"（该状态只由借还业务 3.5/4.3 变更）。
    """

    buyDate = serializers.DateField(source="buy_date", required=False, allow_null=True)
    imgUrl = serializers.CharField(source="img_url", max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=EquipmentStatus.ALL, required=False
    )

    class Meta:
        model = Equipment
        fields = ["name", "model", "spec", "buyDate",
                  "price", "location", "status", "imgUrl", "remark"]
        extra_kwargs = {
            "name": {"max_length": 100, "required": False},
            "model": {"max_length": 100, "required": False},
            "spec": {"max_length": 200, "required": False},
            "location": {"max_length": 200, "required": False},
            "remark": {"max_length": 500, "required": False},
        }


# ================= 响应 Serializer =================

class EquipmentOutSerializer(serializers.ModelSerializer):
    """设备基础信息"""

    equipmentId = serializers.IntegerField(source="id")
    equipmentNo = serializers.CharField(source="equipment_no")
    buyDate = serializers.DateField(source="buy_date", required=False)
    imgUrl = serializers.CharField(source="img_url", required=False, allow_blank=True)
    isDeleted = serializers.BooleanField(source="is_deleted", default=False)
    createTime = serializers.DateTimeField(
        source="create_time", format="%Y-%m-%d %H:%M:%S", required=False
    )

    class Meta:
        model = Equipment
        fields = ["equipmentId", "equipmentNo", "name", "model", "spec",
                  "buyDate", "price", "location", "status", "imgUrl",
                  "remark", "isDeleted", "createTime"]


class BorrowHistorySerializer(serializers.Serializer):
    """2.2 设备详情中的历史借用记录（只读 B 的 borrow_record 表）"""

    recordId = serializers.IntegerField(source="id")
    userId = serializers.IntegerField(source="user_id")
    userName = serializers.CharField(source="user.name", default="")
    userNo = serializers.CharField(source="user.user_no", default="")
    approvalStatus = serializers.CharField(source="approval_status")
    overdueStatus = serializers.CharField(source="overdue_status")
    planBorrowStart = serializers.DateTimeField(
        source="plan_borrow_start", format="%Y-%m-%d %H:%M:%S", required=False
    )
    planReturnTime = serializers.DateTimeField(
        source="plan_return_time", format="%Y-%m-%d %H:%M:%S", required=False
    )
    actualReturnTime = serializers.DateTimeField(
        source="actual_return_time", format="%Y-%m-%d %H:%M:%S", required=False
    )
    returnType = serializers.CharField(source="return_type", default="")
    createTime = serializers.DateTimeField(
        source="create_time", format="%Y-%m-%d %H:%M:%S", required=False
    )


class EquipmentDetailSerializer(EquipmentOutSerializer):
    """2.2 完整设备信息 + 历史借用记录列表"""

    historyRecords = serializers.SerializerMethodField()

    def get_historyRecords(self, obj):
        # 跨域只读：A 只查不写
        records = obj.borrow_records.order_by("-id")[:50]
        return BorrowHistorySerializer(records, many=True).data

    class Meta(EquipmentOutSerializer.Meta):
        fields = EquipmentOutSerializer.Meta.fields + ["historyRecords"]
