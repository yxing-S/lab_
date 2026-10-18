"""
操作日志中间件（G9 切面入口）

仅记录 /api/ 下的写操作（POST/PUT/PATCH/DELETE）；
视图返回后再落库，因此成功/失败、最终状态码都能如实记录。
日志写入任何异常都不会影响业务响应。
"""
from .audit import OperationLogService, _LOG_METHODS


class OperationLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith('/api/') and request.method in _LOG_METHODS:
            try:
                OperationLogService.record(request, response.status_code)
            except Exception:  # noqa: BLE001 - 切面绝不能把业务请求变成 500
                pass

        return response
