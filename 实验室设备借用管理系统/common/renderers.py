"""
统一 JSON 渲染器（配合 G3）

DRF 视图正常返回的裸数据在这里统一包装为 {code, msg, data}；
异常路径由 common.exceptions.custom_exception_handler 生成同样结构，
本渲染器识别到已是标准结构时原样输出，不重复包装。
"""
from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None

        # 已经是标准信封结构（异常处理器或手动 ok()/fail() 产出），直接输出
        if isinstance(data, dict) and {'code', 'msg', 'data'} <= set(data.keys()):
            envelope = data
        elif response is not None and getattr(response, 'exception', False):
            # 兜底：异常响应未被处理器转成标准结构时，按 HTTP 状态码包装
            envelope = {
                'code': response.status_code,
                'msg': '请求异常',
                'data': data,
            }
        else:
            # 正常响应统一包装，默认 200
            envelope = {'code': 200, 'msg': '操作成功', 'data': data}

        return super().render(envelope, accepted_media_type, renderer_context)
