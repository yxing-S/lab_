"""
全局异常处理（G4）

把 DRF / Django 的各类异常统一转换为接口文档第 8 节的标准错误结构：
- 参数校验失败、业务校验失败 → 400
- 未登录 / token 失效          → 401
- 权限不足                     → 403
- 资源不存在                   → 404
- 其他未预期异常               → 500
"""
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from .response import BizError


def _flatten_detail(detail):
    """把 DRF 校验错误结构（dict/list/ErrorDetail）压成一条可读提示"""
    if isinstance(detail, dict):
        for field, value in detail.items():
            text = _flatten_detail(value)
            if text:
                return f'{field}: {text}' if field != 'non_field_errors' else text
    if isinstance(detail, (list, tuple)):
        for item in detail:
            text = _flatten_detail(item)
            if text:
                return text
    return str(detail) if detail else ''


def custom_exception_handler(exc, context):
    # 业务异常：最常见，msg 即给前端看的提示
    if isinstance(exc, BizError):
        return Response(
            {'code': exc.code, 'msg': exc.msg, 'data': exc.data},
            status=exc.code,
        )

    # 先交给 DRF 默认处理器（拿到标准 Response / status_code）
    response = drf_default_handler(exc, context)

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        code, msg = status.HTTP_401_UNAUTHORIZED, '未登录或登录已过期，请重新登录'
    elif isinstance(exc, PermissionDenied):
        code, msg = status.HTTP_403_FORBIDDEN, '权限不足，无该接口访问权限'
    elif isinstance(exc, (Http404, ObjectDoesNotExist)):
        code, msg = status.HTTP_404_NOT_FOUND, '请求的资源不存在'
    elif isinstance(exc, ValidationError):
        msg = _flatten_detail(getattr(exc, 'detail', None)) or '参数校验失败'
        code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, APIException):
        code = response.status_code if response is not None else status.HTTP_400_BAD_REQUEST
        msg = _flatten_detail(getattr(exc, 'detail', None)) or '请求异常'
    else:
        # 未预期异常：生产环境应在这里接日志/告警，不向前端泄露堆栈
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
        msg = '服务器内部异常'

    return Response({'code': code, 'msg': msg, 'data': None}, status=code)
