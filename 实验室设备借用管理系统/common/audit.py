"""
操作日志切面（G9）

用法（注解声明在 DRF 视图类上，中间件自动落库，业务代码零侵入）：

    from rest_framework.views import APIView
    from common.audit import log_operation
    from common.enums import LogModule

    @log_operation(module=LogModule.BORROW, action='提交借用申请')
    class BorrowApplyView(APIView):
        ...

未加注解的写操作按路径前缀推断模块（见 _PATH_MODULE_RULES）。
参数中 password / token 等敏感字段自动脱敏。

注意：G2 会签并执行 makemigrations/migrate 之前，operation_log 表尚不存在，
record() 会静默跳过（仅 debug 日志）；迁移完成后自动开始落库，无需改动业务代码。
"""
import json
import logging

from django.db import DatabaseError

from .enums import LogModule

logger = logging.getLogger(__name__)

# 需要记录的写操作
_LOG_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

# 敏感字段（小写包含匹配），落库前统一打码
_SENSITIVE_HINTS = ('password', 'passwd', 'token', 'secret', 'authorization')

_MAX_PARAMS_LENGTH = 2000

# 路径前缀 -> 模块（顺序敏感：更具体的前缀放前面）
_PATH_MODULE_RULES = (
    ('/api/user/login', LogModule.LOGIN),
    ('/api/admin/user', LogModule.USER),
    ('/api/user', LogModule.USER),
    ('/api/admin/equipment', LogModule.EQUIPMENT),
    ('/api/equipment', LogModule.EQUIPMENT),
    ('/api/borrow', LogModule.BORROW),
    ('/api/admin/borrow', LogModule.BORROW),
    ('/api/admin/statistics', LogModule.BORROW),
    ('/api/admin/export/equipment', LogModule.EQUIPMENT),
    ('/api/admin/export/borrowRecord', LogModule.BORROW),
    ('/api/admin/log', LogModule.OTHER),
)

_DEFAULT_ACTION = {
    'POST': '新增',
    'PUT': '修改',
    'PATCH': '修改',
    'DELETE': '删除',
}


def log_operation(module, action):
    """类装饰器：给 DRF 视图类标记日志模块与动作"""
    def decorate(view_cls):
        view_cls.log_module = module
        view_cls.log_action = action
        return view_cls
    return decorate


def mask_sensitive(data):
    """递归脱敏 dict/list 中的敏感字段"""
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if isinstance(key, str) and any(h in key.lower() for h in _SENSITIVE_HINTS):
                masked[key] = '******'
            else:
                masked[key] = mask_sensitive(value)
        return masked
    if isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    return data


def resolve_module_action(request):
    """
    解析本次操作的模块与动作：
    优先取视图类上的 @log_operation 注解，取不到再按路径 + HTTP 方法推断。
    """
    module, action = None, None

    resolver_match = getattr(request, 'resolver_match', None)
    view_func = getattr(resolver_match, 'func', None)
    view_cls = getattr(view_func, 'cls', None)
    if view_cls is not None:
        module = getattr(view_cls, 'log_module', None)
        action = getattr(view_cls, 'log_action', None)

    if not module:
        for prefix, mod in _PATH_MODULE_RULES:
            if request.path.startswith(prefix):
                module = mod
                break
        else:
            module = LogModule.OTHER

    if not action:
        action = _DEFAULT_ACTION.get(request.method, '操作')

    return module, action


class OperationLogService:
    """操作日志落库服务（中间件调用，也可在业务代码中显式调用）"""

    @staticmethod
    def client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    @staticmethod
    def _extract_params(request):
        """提取并脱敏请求参数；文件上传不记录二进制内容"""
        content_type = request.META.get('CONTENT_TYPE', '')
        try:
            if 'multipart/form-data' in content_type:
                return '文件上传: ' + ', '.join(request.POST.keys())
            if request.method == 'GET':
                raw = dict(request.GET)
            else:
                if not request.body:
                    return ''
                raw = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return '<非 JSON 请求体，已省略>'

        text = json.dumps(mask_sensitive(raw), ensure_ascii=False)
        if len(text) > _MAX_PARAMS_LENGTH:
            text = text[:_MAX_PARAMS_LENGTH] + '...(截断)'
        return text

    @classmethod
    def build_entry(cls, request, status_code):
        """组装日志条目（不写库，供中间件调用/也便于单测）"""
        user = getattr(request, 'user', None)
        is_authenticated = bool(user is not None and getattr(user, 'is_authenticated', False))
        module, action = resolve_module_action(request)

        return {
            'operator_id': user.pk if is_authenticated else None,
            'operator_name': (
                getattr(user, 'name', '') or user.get_username()
                if is_authenticated else ''
            ),
            'module': module,
            'action': action,
            'method': request.method,
            'path': request.path[:255],
            'params': cls._extract_params(request),
            'ip': cls.client_ip(request),
            'success': status_code < 400,
            'status_code': status_code,
        }

    @classmethod
    def record(cls, request, status_code):
        """写一条操作日志；任何异常都不得影响主请求"""
        from .models import OperationLog
        try:
            OperationLog.objects.create(**cls.build_entry(request, status_code))
        except DatabaseError:
            # G2 会签迁移前 operation_log 表不存在，静默跳过；迁移后自动生效
            logger.debug('operation_log 表不可用，跳过日志写入（待 G2 迁移）')
        except Exception:  # noqa: BLE001 - 日志切面永远不能阻断业务
            logger.exception('操作日志写入异常')
