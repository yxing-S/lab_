"""
权限校验（B 侧临时实现）

G7「角色权限校验 + @RequireAdmin」由 A 牵头、尚未交付；
B 的 /api/admin/** 接口先由本文件 IsAdmin 等价兜底，待 A 交付 G7 后替换为统一鉴权即可。

兼容两套用户模型：
- 当前 auth.User（无 role 字段，用 is_staff 判断，超管可访问）
- A 的自定义 User（role=admin 或 is_staff 均可判定为管理员）

越权返回 403，由 common.exceptions.custom_exception_handler 统一转译。
"""
from rest_framework.permissions import BasePermission

from .enums import UserRole


class IsAdmin(BasePermission):
    """仅管理员可访问"""

    message = '权限不足，仅管理员可访问该接口'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_staff', False):
            return True
        return getattr(user, 'role', None) == UserRole.ADMIN
