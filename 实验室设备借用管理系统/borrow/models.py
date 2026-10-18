"""
借用记录模型（borrow_record，G2 会签稿，开发者 B）

当前为「无外键」版本：user_id / equipment_id 用整数字段暂存，
便于在 A 的 user / equipment 模型尚未并入项目时即可迁移、B 域独立跑通。

待 A 的模型并入后，将 user_id / equipment_id 改为外键（列名不变，迁移平滑）：
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, ...)
    equipment = models.ForeignKey('equipment.Equipment', on_delete=models.PROTECT, ...)

字段取值复用 common.enums：BorrowApprovalStatus / OverdueStatus / ReturnType。
"""
from django.db import models

from common.enums import BorrowApprovalStatus, OverdueStatus, ReturnType


class BorrowRecord(models.Model):
    # 申请人 / 设备：暂用整数字段，待 A 模型并入后改外键（见模块 docstring）
    user_id = models.PositiveIntegerField('申请人ID', db_index=True)
    equipment_id = models.PositiveIntegerField('设备ID', db_index=True)

    plan_borrow_start = models.DateTimeField('计划借用开始时间')
    plan_return_time = models.DateTimeField('计划归还时间')
    borrow_purpose = models.CharField('借用用途', max_length=200)
    remark = models.CharField('备注', max_length=500, blank=True, default='')

    approval_status = models.CharField(
        '审批状态', max_length=20,
        choices=BorrowApprovalStatus.choices,
        default=BorrowApprovalStatus.PENDING,
    )
    overdue_status = models.CharField(
        '逾期状态', max_length=20,
        choices=OverdueStatus.choices,
        default=OverdueStatus.NORMAL,
    )
    audit_opinion = models.CharField('审批意见', max_length=500, blank=True, default='')
    audit_time = models.DateTimeField('审批时间', null=True, blank=True)
    cancel_time = models.DateTimeField('取消时间', null=True, blank=True)
    return_apply_time = models.DateTimeField('发起归还时间', null=True, blank=True)
    actual_return_time = models.DateTimeField('实际归还时间', null=True, blank=True)
    return_type = models.CharField(
        '归还类型', max_length=20,
        choices=ReturnType.choices,
        null=True, blank=True,
    )

    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'borrow_record'
        verbose_name = '借用记录'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['approval_status'], name='borrow_aprv_status_idx'),
            models.Index(fields=['overdue_status'], name='borrow_od_status_idx'),
            models.Index(fields=['plan_return_time'], name='borrow_plan_return_idx'),
        ]

    def __str__(self):
        return f'{self.id} 用户{self.user_id} 设备{self.equipment_id} {self.approval_status}'
