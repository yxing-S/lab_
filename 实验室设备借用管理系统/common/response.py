"""
统一返回格式（G3，B 先出会签稿，待 A 冻结）

接口文档第 3 节：
{
    "code": 200,          # 200成功 / 400参数或业务错误 / 401未登录 / 403无权限 / 404不存在 / 500异常
    "msg": "操作提示信息",
    "data": {}            # 失败时为 null
}

约定：HTTP 状态码与业务 code 保持一致，前端既可读 HTTP 状态，也可读 body.code。
"""


class BizError(Exception):
    """业务逻辑异常：视图中主动 raise，由全局异常处理器统一捕获（G4）"""

    def __init__(self, msg='业务处理失败', code=400, data=None):
        self.msg = msg
        self.code = code
        self.data = data
        super().__init__(msg)


def ok(data=None, msg='操作成功'):
    """成功响应（如需在视图里显式返回时使用）"""
    from rest_framework.response import Response
    return Response({'code': 200, 'msg': msg, 'data': data}, status=200)


def fail(msg='操作失败', code=400, data=None, http_status=None):
    """失败响应（一般直接 raise BizError 即可，无需手动调本函数）"""
    from rest_framework.response import Response
    return Response(
        {'code': code, 'msg': msg, 'data': data},
        status=http_status or code,
    )
