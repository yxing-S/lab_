"""
标准分页（G5）

请求参数：page（页码，默认 1）、size（每页条数，默认 10）
返回字段（接口文档第 4 节）：total、pages、current、records
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    page_query_param = 'page'
    page_size_query_param = 'size'
    page_size = 10
    max_page_size = 100  # 同时作为导出条数上限的参考值（5.3 / 5.4）

    def get_paginated_response(self, data):
        return Response({
            'total': self.page.paginator.count,
            'pages': self.page.paginator.num_pages,
            'current': self.page.number,
            'records': data,
        })
