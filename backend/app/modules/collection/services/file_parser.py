"""
文件解析工具：从 CSV / XLSX 中读取表头和数据行。

返回统一格式：
  - columns: list[str]           — 列头列表
  - rows: list[dict[str, str]]   — 每行数据，key=列头，value=字符串值
"""
import csv
import io
from typing import BinaryIO


def parse_file(file_bytes: bytes, filename: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    解析上传文件，返回 (columns, rows)。
    支持 .csv / .xlsx。
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        return _parse_csv(file_bytes)
    elif ext in ("xlsx", "xls"):
        return _parse_xlsx(file_bytes)
    else:
        raise ValueError(f"不支持的文件格式: .{ext}（仅支持 csv / xlsx）")


def _parse_csv(data: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = data.decode("utf-8-sig")  # 处理 BOM
    reader = csv.DictReader(io.StringIO(text))
    columns = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    return columns, rows


def _parse_xlsx(data: bytes) -> tuple[list[str], list[dict[str, str]]]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(c) if c is not None else "" for c in next(rows_iter, [])]
    rows = []
    for row in rows_iter:
        if all(v is None for v in row):
            continue  # 跳过空行
        rows.append({header[i]: (str(v) if v is not None else "") for i, v in enumerate(row)})
    wb.close()
    return header, rows
