"""
Excel 导入 / 导出最小工具（G10，基于 openpyxl）

供 B 的 5.4 借用记录导出，以及 A 的 1.12 / 2.6 批量导入复用：
- read_excel_rows：读取上传文件，第一行作为表头，返回 [{表头: 单元格值}, ...]
- write_excel_response：给定表头与数据行，返回 xlsx 文件下载 HttpResponse
"""
import io

from django.http import HttpResponse
from openpyxl import Workbook, load_workbook


def read_excel_rows(file_obj):
    """
    读取上传的 Excel（form-data 中的文件对象）。
    第一行为表头，返回 (表头列表, 行字典列表)。
    空文件返回 ([], [])。
    """
    wb = load_workbook(filename=file_obj, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []

    headers = [str(cell).strip() if cell is not None else '' for cell in rows[0]]
    result = []
    for raw in rows[1:]:
        # 整行全空则跳过
        if all(cell is None or str(cell).strip() == '' for cell in raw):
            continue
        result.append({
            headers[i]: raw[i] if i < len(raw) else None
            for i in range(len(headers))
            if headers[i]
        })
    return headers, result


def write_excel_response(filename, headers, rows):
    """
    生成 xlsx 下载流。
    :param filename: 浏览器保存的文件名（无需 .xlsx 后缀也会自动补）
    :param headers:  ['设备编号', '设备名称', ...]
    :param rows:     [['DEV-0001', '示波器', ...], ...] 或 [dict, ...]（dict 时按 headers 取值）
    """
    wb = Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append(headers)

    for row in rows:
        if isinstance(row, dict):
            ws.append([row.get(h, '') for h in headers])
        else:
            ws.append(list(row))

    if not filename.endswith('.xlsx'):
        filename += '.xlsx'

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
