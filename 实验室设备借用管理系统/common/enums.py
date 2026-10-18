"""
通用枚举与字典常量（G11）

说明：
- 设备状态、用户状态的取值与 equipment / users 域共享，G2 表结构会签后冻结，
  开发者 A 的模型 choices 直接引用这里，避免两处维护不一致。
- 借用审批状态、逾期状态、归还类型归 B 的 borrow 域使用。
"""
from django.db import models


class EquipmentStatus(models.TextChoices):
    """设备状态（接口文档 7.1）"""
    IDLE = '闲置', '闲置'
    BORROWED = '借出中', '借出中'
    REPAIRING = '维修中', '维修中'
    SCRAPPED = '已报废', '已报废'


class BorrowApprovalStatus(models.TextChoices):
    """借用审批状态（接口文档 3.2 筛选值 / 7.2）"""
    PENDING = '待审批', '待审批'
    APPROVED = '已通过', '已通过'
    REJECTED = '已驳回', '已驳回'
    CANCELED = '已取消', '已取消'
    RETURNED = '已归还', '已归还'


class OverdueStatus(models.TextChoices):
    """
    逾期状态（G12）
    - 正常：未逾期
    - 已逾期：已通过且超过 plan_return_time 仍未归还（3.1 据此拦截新申请）
    - 逾期已归还：确认归还时实际归还时间晚于计划归还时间（4.3）
    """
    NORMAL = '正常', '正常'
    OVERDUE = '已逾期', '已逾期'
    OVERDUE_RETURNED = '逾期已归还', '逾期已归还'


class ReturnType(models.TextChoices):
    """归还结果（接口文档 4.3）"""
    NORMAL = 'normal', '正常归还'
    DAMAGE = 'damage', '损坏'
    LOSE = 'lose', '丢失损毁'


class AuditResult(models.TextChoices):
    """审批结果（接口文档 3.5）"""
    PASS = 'pass', '通过'
    REJECT = 'reject', '驳回'


class UserRole(models.TextChoices):
    """角色标识（接口文档第 2 节）"""
    ADMIN = 'admin', '管理员'
    USER = 'user', '普通用户'


class UserStatus(models.TextChoices):
    """用户账号状态（接口文档 1.2 / 1.10）"""
    NORMAL = '正常', '正常'
    DISABLED = '禁用', '禁用'


# ---- 操作日志模块（6.1 module 筛选用，G9 落库时取中文值）----
class LogModule(models.TextChoices):
    USER = '用户管理', '用户管理'
    EQUIPMENT = '设备管理', '设备管理'
    BORROW = '借用审批', '借用审批'
    RETURN = '归还管理', '归还管理'
    LOGIN = '登录认证', '登录认证'
    OTHER = '其他', '其他'


# 字典接口返回顺序固定（7.1 / 7.2）
EQUIPMENT_STATUS_DICT = [label for _, label in EquipmentStatus.choices]
BORROW_STATUS_DICT = [label for _, label in BorrowApprovalStatus.choices]

# ---- 兼容 A 的 apps.common.constants 命名（方案B：本文件为唯一来源）----
# A 的模型用 Role（本文件为 UserRole）、ApprovalStatus（本文件为 BorrowApprovalStatus），
# 值完全一致，别名让 A 无需改类名即可 import。
# 注意：A 的 ApprovalStatus.PASSED 对应本文件的 BorrowApprovalStatus.APPROVED（成员名不同）。
Role = UserRole
ApprovalStatus = BorrowApprovalStatus
