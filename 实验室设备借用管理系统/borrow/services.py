"""
借用业务服务层（开发者 B）

分层：serializer（无表校验）-> services（业务/事务）-> 标准返回。

状态：
- borrow_record 表已迁移，本域查询与落库可直接运行；
- 依赖 A 的 equipment 表的读写（设备状态校验/流转）由 EQUIPMENT_READY 开关挡着，
  A 的 equipment 模型并入并迁移后置 True 即可，接口层无需改动。

接口文档落点：
  3.1 ①设备闲置校验 / ②时间规则(序列化器) / ③逾期未还拦截 / ④时间冲突校验
  3.5 审批：pass 事务同步设备改"借出中"；reject 仅改记录
  4.3 确认归还：事务同步记录与设备状态（normal/damage/lose）
  5.1 / 5.2 统计聚合（借用次数 / 时长 / 逾期次数）
"""
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from common.enums import (
    AuditResult,
    BorrowApprovalStatus,
    EquipmentStatus,
    OverdueStatus,
    ReturnType,
    UserStatus,
)
from common.response import BizError


# ============================================================
# 纯业务规则（G12 / 3.1 / 4.3）—— 不依赖数据库表，可独立单测
# ============================================================

def compute_overdue_status(plan_return_time, actual_return_time=None, now=None):
    """
    G12 逾期状态判定（纯逻辑）：
    - 尚未归还：当前时间晚于计划归还时间 -> 已逾期；否则 -> 正常
    - 已归还：实际归还时间晚于计划归还时间 -> 逾期已归还；否则 -> 正常
    """
    now = now or timezone.now()
    if actual_return_time is None:
        return OverdueStatus.OVERDUE if now > plan_return_time else OverdueStatus.NORMAL
    return OverdueStatus.OVERDUE_RETURNED if actual_return_time > plan_return_time else OverdueStatus.NORMAL


def time_overlaps(start1, end1, start2, end2):
    """两个时间段是否重叠：start1 < end2 且 start2 < end1，端点相接不算重叠。"""
    return start1 < end2 and start2 < end1


def equipment_status_after_return(return_type):
    """4.3 归还后设备状态流转：normal->闲置；damage->维修中；lose->已报废；未知->None。"""
    return {
        ReturnType.NORMAL: EquipmentStatus.IDLE,
        ReturnType.DAMAGE: EquipmentStatus.REPAIRING,
        ReturnType.LOSE: EquipmentStatus.SCRAPPED,
    }.get(return_type)


# ============================================================
# 跨域开关与设备状态读写（A 的 equipment 域）
# ============================================================

# A 的 equipment 模型尚未并入项目；并入并迁移后置 True，接口层无需改动
EQUIPMENT_READY = False
_EQUIPMENT_NOT_READY_MSG = '设备状态流转暂未开放：等待 A 的 equipment 模型并入并迁移'


def _equipment_objects():
    """获取 equipment 表的 ORM 入口；模型未并入前抛出明确提示。"""
    if not EQUIPMENT_READY:
        raise BizError(_EQUIPMENT_NOT_READY_MSG)
    from equipment.models import Equipment
    return Equipment.objects


def check_equipment_borrowable(equipment_id):
    """校验 ①：设备存在、未逻辑删除、状态为"闲置"（3.1）。"""
    equipment = _equipment_objects().filter(pk=equipment_id).first()
    if equipment is None:
        raise BizError('设备不存在', code=404)
    if equipment.is_deleted:
        raise BizError('设备已删除，无法借用')
    if equipment.status != EquipmentStatus.IDLE:
        raise BizError('该设备当前不是闲置状态')
    return equipment


def set_equipment_status(equipment_id, status):
    """写设备状态（3.5 通过 -> 借出中；4.3 -> 闲置/维修中/已报废）。"""
    updated = _equipment_objects().filter(pk=equipment_id).update(status=status)
    if updated == 0:
        raise BizError('设备不存在，无法更新状态', code=404)


def ensure_user_active(user):
    """1.10 + 3.1：禁用账号禁止新建借用申请（读 A 的 user.status，缺省视为正常）。"""
    if getattr(user, 'status', UserStatus.NORMAL) == UserStatus.DISABLED:
        raise BizError('账号已被禁用，无法提交借用申请')


# ============================================================
# 借用记录查询与校验（本域 borrow_record，已迁移可直接运行）
# ============================================================

def has_overdue_unreturned(user_id):
    """校验 ③：当前用户存在"已逾期"且未归还的记录 -> True。"""
    from .models import BorrowRecord
    return BorrowRecord.objects.filter(
        user_id=user_id,
        approval_status=BorrowApprovalStatus.APPROVED,
        overdue_status=OverdueStatus.OVERDUE,
        actual_return_time__isnull=True,
    ).exists()


def has_approved_time_conflict(equipment_id, start, end):
    """校验 ④：仅"已通过"且未归还的记录参与时间段重叠判断。"""
    from .models import BorrowRecord
    return BorrowRecord.objects.filter(
        equipment_id=equipment_id,
        approval_status=BorrowApprovalStatus.APPROVED,
        actual_return_time__isnull=True,
        plan_borrow_start__lt=end,
        plan_return_time__gt=start,
    ).exists()


def create_borrow_record(user, data):
    """创建借用记录（默认"待审批" / "正常"）。"""
    from .models import BorrowRecord
    return BorrowRecord.objects.create(
        user_id=user.id,
        equipment_id=data['equipmentId'],
        plan_borrow_start=data['planBorrowStart'],
        plan_return_time=data['planReturnTime'],
        borrow_purpose=data['borrowPurpose'],
        remark=data.get('remark', ''),
        approval_status=BorrowApprovalStatus.PENDING,
        overdue_status=OverdueStatus.NORMAL,
    )


@transaction.atomic
def apply_borrow(user, data):
    """3.1 提交借用申请：设备可借 -> 用户未禁用 -> 无逾期未还 -> 无时间冲突 -> 落库。"""
    check_equipment_borrowable(data['equipmentId'])
    ensure_user_active(user)
    if has_overdue_unreturned(user.id):
        raise BizError('存在逾期未还记录，禁止申请')
    if has_approved_time_conflict(data['equipmentId'], data['planBorrowStart'], data['planReturnTime']):
        raise BizError('该设备在所选时间段已被借出，请调整借用时间')
    return create_borrow_record(user, data)


# ---- 3.2 / 3.3 ----

def query_my_borrow(user_id, approval_status=None):
    """3.2 我的申请列表：只能查自己，可按审批状态筛选。"""
    from .models import BorrowRecord
    qs = BorrowRecord.objects.filter(user_id=user_id)
    if approval_status:
        qs = qs.filter(approval_status=approval_status)
    return qs.order_by('-create_time')


def cancel_borrow(user_id, record_id):
    """3.3 取消待审批申请：归属当前用户且仅"待审批"可取消，写 cancel_time。"""
    from .models import BorrowRecord
    record = BorrowRecord.objects.filter(pk=record_id, user_id=user_id).first()
    if record is None:
        raise BizError('借用记录不存在或不属于当前用户', code=404)
    if record.approval_status != BorrowApprovalStatus.PENDING:
        raise BizError('仅待审批的申请可取消')
    record.approval_status = BorrowApprovalStatus.CANCELED
    record.cancel_time = timezone.now()
    record.save(update_fields=['approval_status', 'cancel_time'])
    return record


# ---- 3.4 / 3.5 / 3.6 ----

def query_pending_borrow():
    """3.4 待审批列表。"""
    from .models import BorrowRecord
    return BorrowRecord.objects.filter(
        approval_status=BorrowApprovalStatus.PENDING,
    ).order_by('create_time')


@transaction.atomic
def audit_borrow(record_id, result, opinion=''):
    """3.5 审批：pass 事务同步设备改"借出中"；reject 仅改记录；禁止重复审批。"""
    from .models import BorrowRecord
    record = BorrowRecord.objects.select_for_update().filter(pk=record_id).first()
    if record is None:
        raise BizError('借用记录不存在', code=404)
    if record.approval_status != BorrowApprovalStatus.PENDING:
        raise BizError('该申请已审批，禁止重复审批')

    record.audit_opinion = opinion
    record.audit_time = timezone.now()
    if result == AuditResult.PASS:
        record.approval_status = BorrowApprovalStatus.APPROVED
        record.save(update_fields=['approval_status', 'audit_opinion', 'audit_time'])
        set_equipment_status(record.equipment_id, EquipmentStatus.BORROWED)
    else:
        record.approval_status = BorrowApprovalStatus.REJECTED
        record.save(update_fields=['approval_status', 'audit_opinion', 'audit_time'])
    return record


def query_all_borrow(user_id=None, equipment_id=None, start_time=None, end_time=None, overdue_status=None):
    """3.6 全部借用记录：按用户 / 设备 / 借用时间范围 / 逾期状态筛选。"""
    from .models import BorrowRecord
    qs = BorrowRecord.objects.all()
    if user_id:
        qs = qs.filter(user_id=user_id)
    if equipment_id:
        qs = qs.filter(equipment_id=equipment_id)
    if start_time:
        qs = qs.filter(plan_borrow_start__gte=start_time)
    if end_time:
        qs = qs.filter(plan_borrow_start__lte=end_time)
    if overdue_status:
        qs = qs.filter(overdue_status=overdue_status)
    return qs.order_by('-create_time')


# ---- 4.1 / 4.2 / 4.3 ----

def apply_return(user_id, record_id):
    """4.1 发起归还：归属当前用户、状态"已通过"、不可重复提交。"""
    from .models import BorrowRecord
    record = BorrowRecord.objects.filter(pk=record_id, user_id=user_id).first()
    if record is None:
        raise BizError('借用记录不存在或不属于当前用户', code=404)
    if record.approval_status != BorrowApprovalStatus.APPROVED:
        raise BizError('仅已通过（借出中）的记录可发起归还')
    if record.return_apply_time is not None:
        raise BizError('已发起归还申请，不可重复提交')
    record.return_apply_time = timezone.now()
    record.save(update_fields=['return_apply_time'])
    return record


def query_wait_return():
    """4.2 待归还列表：已通过 + 已发起归还 + 尚未确认归还。"""
    from .models import BorrowRecord
    return BorrowRecord.objects.filter(
        approval_status=BorrowApprovalStatus.APPROVED,
        return_apply_time__isnull=False,
        actual_return_time__isnull=True,
    ).order_by('return_apply_time')


@transaction.atomic
def confirm_return(record_id, return_type, remark=''):
    """4.3 确认归还：事务同步记录与设备状态；按实际归还时间自动设逾期状态。"""
    from .models import BorrowRecord
    record = BorrowRecord.objects.filter(pk=record_id).first()
    if record is None:
        raise BizError('借用记录不存在', code=404)
    if record.actual_return_time is not None:
        raise BizError('该记录已确认归还，禁止重复操作')

    now = timezone.now()
    record.actual_return_time = now
    record.return_type = return_type
    record.overdue_status = compute_overdue_status(record.plan_return_time, actual_return_time=now)
    record.approval_status = BorrowApprovalStatus.RETURNED
    if remark:
        record.audit_opinion = remark
    record.save(update_fields=[
        'actual_return_time', 'return_type', 'overdue_status',
        'approval_status', 'audit_opinion',
    ])
    set_equipment_status(record.equipment_id, equipment_status_after_return(return_type))
    return record


# ============================================================
# 5.1 / 5.2 / 5.4 统计与导出
# ============================================================

def equipment_statistics():
    """
    5.1 设备借用统计（按 equipment_id 聚合）：
    - borrowCount：借用总次数（已通过 / 已归还，即实际借用过）
    - totalBorrowHours：累计借用时长（小时，未归还按当前时间计）
    - idleHours：闲置时长 = 自首次借用以来的总时长 - 累计借用时长（小时）
    """
    from .models import BorrowRecord
    now = timezone.now()
    records = BorrowRecord.objects.filter(
        approval_status__in=[BorrowApprovalStatus.APPROVED, BorrowApprovalStatus.RETURNED],
    ).values('equipment_id', 'plan_borrow_start', 'actual_return_time')

    stats = {}
    for r in records:
        s = stats.setdefault(r['equipment_id'], {'count': 0, 'seconds': 0.0, 'first_start': None})
        start = r['plan_borrow_start']
        end = r['actual_return_time'] or now
        s['count'] += 1
        s['seconds'] += max(0.0, (end - start).total_seconds())
        if s['first_start'] is None or start < s['first_start']:
            s['first_start'] = start

    result = []
    for equipment_id, s in stats.items():
        window = (now - s['first_start']).total_seconds() if s['first_start'] else 0.0
        result.append({
            'equipmentId': equipment_id,
            'borrowCount': s['count'],
            'totalBorrowHours': round(s['seconds'] / 3600, 2),
            'idleHours': round(max(0.0, window - s['seconds']) / 3600, 2),
        })
    result.sort(key=lambda x: x['borrowCount'], reverse=True)
    return result


def user_statistics():
    """
    5.2 用户借用统计（按 user_id 聚合）：
    - borrowCount：借用总次数（已通过 / 已归还）
    - overdueCount：逾期次数（已逾期 / 逾期已归还）
    """
    from .models import BorrowRecord
    rows = BorrowRecord.objects.values('user_id').annotate(
        borrowCount=Count(
            'id',
            filter=Q(approval_status__in=[BorrowApprovalStatus.APPROVED, BorrowApprovalStatus.RETURNED]),
        ),
        overdueCount=Count(
            'id',
            filter=Q(overdue_status__in=[OverdueStatus.OVERDUE, OverdueStatus.OVERDUE_RETURNED]),
        ),
    ).order_by('-borrowCount')
    return [
        {'userId': r['user_id'], 'borrowCount': r['borrowCount'], 'overdueCount': r['overdueCount']}
        for r in rows
    ]


def query_export_borrow(start_time=None, end_time=None):
    """5.4 导出借用记录：按借用时间范围筛选。"""
    from .models import BorrowRecord
    qs = BorrowRecord.objects.all()
    if start_time:
        qs = qs.filter(plan_borrow_start__gte=start_time)
    if end_time:
        qs = qs.filter(plan_borrow_start__lte=end_time)
    return qs.order_by('create_time')
