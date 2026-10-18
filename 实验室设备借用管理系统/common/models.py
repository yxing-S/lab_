"""
操作日志模型（G9）—— G2 会签稿，会签前暂不执行 makemigrations

对应接口文档 6.1：GET /api/admin/log/list?page=1&module=&operatorId=&startTime=&endTime=
落库方式：由 common.middleware.OperationLogMiddleware 在关键操作后自动写入，
业务代码通过 @log_operation(module=..., action=...) 注解声明模块与动作。

会签确认点：
1. operator_id 暂用整数字段（无外键），待 A 的自定义 User 并入后再改外键（列名不变）；
   operator_name 冗余快照，用户删除后仍可查。
2. module 取值见 common.enums.LogModule（用户管理/设备管理/借用审批/归还管理/登录认证/其他）。
"""
from django.db import models

from .enums import LogModule


class OperationLog(models.Model):
    # 操作人：暂用整数字段（无外键），待 A 的自定义 User 并入后再改外键（列名 operator_id 不变）
    operator_id = models.PositiveIntegerField('操作人ID', null=True, blank=True)
    # 冗余姓名快照，避免用户被删除后日志无法辨认操作人
    operator_name = models.CharField('操作人姓名', max_length=64, blank=True, default='')

    module = models.CharField('功能模块', max_length=20, choices=LogModule.choices)
    action = models.CharField('操作动作', max_length=64)
    method = models.CharField('请求方法', max_length=10)
    path = models.CharField('请求路径', max_length=255)
    params = models.TextField('请求参数（脱敏摘要）', blank=True, default='')
    ip = models.CharField('IP 地址', max_length=40, blank=True, default='')
    success = models.BooleanField('是否成功', default=True)
    status_code = models.PositiveSmallIntegerField('HTTP 状态码', default=0)
    create_time = models.DateTimeField('操作时间', auto_now_add=True)

    class Meta:
        db_table = 'operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['module'], name='oplog_module_idx'),
            models.Index(fields=['operator_id'], name='oplog_operator_idx'),
            models.Index(fields=['create_time'], name='oplog_time_idx'),
        ]

    def __str__(self):
        return f'{self.create_time:%Y-%m-%d %H:%M:%S} {self.operator_name} {self.action}'
