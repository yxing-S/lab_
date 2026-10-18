from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from common.enums import EquipmentStatus, OverdueStatus, ReturnType
from .serializers import (
    BorrowAllListQuerySerializer,
    BorrowAuditSerializer,
    BorrowExportQuerySerializer,
    BorrowMyListQuerySerializer,
    ReturnConfirmSerializer,
)
from .services import (
    compute_overdue_status,
    equipment_status_after_return,
    time_overlaps,
)


class ComputeOverdueStatusTests(SimpleTestCase):
    """G12 逾期状态判定（纯逻辑）"""

    def test_not_returned_and_past_due(self):
        now = timezone.now()
        plan = now - timedelta(hours=1)
        self.assertEqual(compute_overdue_status(plan, now=now), OverdueStatus.OVERDUE)

    def test_not_returned_and_not_due(self):
        now = timezone.now()
        plan = now + timedelta(hours=1)
        self.assertEqual(compute_overdue_status(plan, now=now), OverdueStatus.NORMAL)

    def test_returned_late(self):
        now = timezone.now()
        plan = now - timedelta(hours=1)
        self.assertEqual(
            compute_overdue_status(plan, actual_return_time=now, now=now),
            OverdueStatus.OVERDUE_RETURNED,
        )

    def test_returned_on_time(self):
        now = timezone.now()
        plan = now + timedelta(hours=1)
        self.assertEqual(
            compute_overdue_status(plan, actual_return_time=now, now=now),
            OverdueStatus.NORMAL,
        )


class TimeOverlapsTests(SimpleTestCase):
    """3.1 校验④ 时间段重叠判断（纯逻辑）"""

    def test_overlap(self):
        now = timezone.now()
        self.assertTrue(
            time_overlaps(
                now - timedelta(hours=1), now + timedelta(hours=1),
                now, now + timedelta(hours=2),
            )
        )

    def test_no_overlap(self):
        now = timezone.now()
        self.assertFalse(
            time_overlaps(
                now, now + timedelta(hours=1),
                now + timedelta(hours=2), now + timedelta(hours=3),
            )
        )

    def test_adjacent_is_no_overlap(self):
        now = timezone.now()
        self.assertFalse(
            time_overlaps(
                now, now + timedelta(hours=1),
                now + timedelta(hours=1), now + timedelta(hours=2),
            )
        )


class EquipmentStatusAfterReturnTests(SimpleTestCase):
    """4.3 归还结果 -> 设备状态流转映射（纯逻辑）"""

    def test_normal_to_idle(self):
        self.assertEqual(equipment_status_after_return(ReturnType.NORMAL), EquipmentStatus.IDLE)

    def test_damage_to_repairing(self):
        self.assertEqual(equipment_status_after_return(ReturnType.DAMAGE), EquipmentStatus.REPAIRING)

    def test_lose_to_scrapped(self):
        self.assertEqual(equipment_status_after_return(ReturnType.LOSE), EquipmentStatus.SCRAPPED)

    def test_unknown_returns_none(self):
        self.assertIsNone(equipment_status_after_return('unknown'))


class BorrowAuditSerializerTests(SimpleTestCase):
    """3.5 审批序列化器校验"""

    def test_pass_without_opinion_ok(self):
        s = BorrowAuditSerializer(data={'result': 'pass'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_reject_without_opinion_invalid(self):
        s = BorrowAuditSerializer(data={'result': 'reject'})
        self.assertFalse(s.is_valid())

    def test_reject_with_opinion_ok(self):
        s = BorrowAuditSerializer(data={'result': 'reject', 'opinion': '时间冲突'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_result(self):
        s = BorrowAuditSerializer(data={'result': 'x'})
        self.assertFalse(s.is_valid())


class ReturnConfirmSerializerTests(SimpleTestCase):
    """4.3 确认归还序列化器校验"""

    def test_valid(self):
        s = ReturnConfirmSerializer(data={'returnType': 'normal'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid(self):
        s = ReturnConfirmSerializer(data={'returnType': 'x'})
        self.assertFalse(s.is_valid())

    def test_missing(self):
        s = ReturnConfirmSerializer(data={})
        self.assertFalse(s.is_valid())


class BorrowQuerySerializerTests(SimpleTestCase):
    """3.2 / 3.6 / 5.4 查询参数校验"""

    def test_my_list_valid(self):
        s = BorrowMyListQuerySerializer(data={'approvalStatus': '待审批'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_my_list_invalid_status(self):
        s = BorrowMyListQuerySerializer(data={'approvalStatus': '不存在'})
        self.assertFalse(s.is_valid())

    def test_all_list_valid(self):
        s = BorrowAllListQuerySerializer(data={'startTime': '2026-10-12 10:00:00', 'overdueStatus': '已逾期'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_all_list_invalid_time_format(self):
        s = BorrowAllListQuerySerializer(data={'startTime': '2026-10-12'})
        self.assertFalse(s.is_valid())

    def test_export_valid(self):
        s = BorrowExportQuerySerializer(data={'startTime': '2026-10-12 10:00:00', 'endTime': '2026-10-13 10:00:00'})
        self.assertTrue(s.is_valid(), s.errors)
