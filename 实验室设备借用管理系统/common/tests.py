from django.test import SimpleTestCase

from .serializers import OperationLogQuerySerializer


class OperationLogQuerySerializerTests(SimpleTestCase):
    """6.1 操作日志查询参数校验"""

    def test_valid(self):
        s = OperationLogQuerySerializer(data={
            'module': '设备管理', 'operatorId': 1, 'startTime': '2026-10-12 10:00:00',
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_module(self):
        s = OperationLogQuerySerializer(data={'module': '不存在'})
        self.assertFalse(s.is_valid())

    def test_invalid_time_format(self):
        s = OperationLogQuerySerializer(data={'startTime': '2026-10-12'})
        self.assertFalse(s.is_valid())
