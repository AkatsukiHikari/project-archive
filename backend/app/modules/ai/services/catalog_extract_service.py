"""智能著录 - AI 抽取。

从原文全文(full_text)按门类字段 schema 抽结构化著录数据，走 Dify「智能著录抽取」工作流。
- extract_from_text：已有全文 → 抽取
- ocr_file_bytes：上传的 PDF/OFD 字节 → 经 OCR 工作流取全文（自动录入用）
"""

import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.common.error_code import ErrorCode
from app.common.exceptions.base import ValidationException
from app.modules.ai.services.dify_service import dify_service

logger = logging.getLogger(__name__)

# 可写入档案模型列的基础字段（其余进 ext_fields）
BASE_COLUMNS = {"DH", "TM", "RZZ", "ND", "MJ", "BGQX", "WJRQ", "YS", "QZH"}


def compact_schema(field_schema: Optional[list]) -> list[dict]:
    """门类 field_schema → 抽取所需的精简字段定义。

    按 sort_order 排序；sort_order=0/缺失(多为门类特殊字段)排到最后，
    保证 档号→题名→…→特殊字段 的合理顺序，与著录表单一致。
    """
    def _ord(f: dict) -> int:
        so = f.get("sort_order")
        return so if isinstance(so, int) and so > 0 else 9999

    out: list[dict] = []
    for f in sorted(
        [f for f in (field_schema or []) if isinstance(f, dict) and f.get("name")],
        key=_ord,
    ):
        out.append(
            {
                "name": f.get("name"),
                "label": f.get("label") or f.get("name"),
                "type": f.get("type") or "text",
                "required": bool(f.get("required")),
                "options": [
                    o.get("value") if isinstance(o, dict) else o
                    for o in (f.get("options") or [])
                ],
            }
        )
    return out


def _parse_json_obj(text: str) -> dict:
    """从模型输出里稳健地取出 JSON 对象（容忍 ```json 包裹、前后杂字）。"""
    if not text:
        return {}
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        data = json.loads(s[start : end + 1])
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        logger.warning("智能著录：抽取结果非合法 JSON")
        return {}


def _normalize(raw: dict) -> dict[str, dict]:
    """统一成 {name: {value, confidence, evidence}}。"""
    out: dict[str, dict] = {}
    for name, v in (raw or {}).items():
        if isinstance(v, dict):
            out[name] = {
                "value": "" if v.get("value") is None else str(v.get("value")).strip(),
                "confidence": int(v.get("confidence") or 0),
                "evidence": str(v.get("evidence") or "")[:200],
            }
        else:
            out[name] = {"value": str(v).strip(), "confidence": 60, "evidence": ""}
    return out


async def extract_from_text(
    full_text: str,
    field_schema: Optional[list],
    existing: dict[str, Any],
    user_id: str,
) -> dict[str, dict]:
    """调 Dify 智能著录工作流，返回 {字段: {value, confidence, evidence}}。"""
    key = settings.DIFY_CATALOG_WORKFLOW_KEY
    if not key:
        raise ValidationException(
            message="未配置智能著录工作流（DIFY_CATALOG_WORKFLOW_KEY）"
        )
    if not (full_text or "").strip():
        raise ValidationException(message="该档案暂无原文全文，请先 OCR 识别原文")

    schema = compact_schema(field_schema)
    outputs = await dify_service.run_workflow(
        inputs={
            "full_text": full_text[:48000],
            "field_schema": json.dumps(schema, ensure_ascii=False),
            "existing": json.dumps(existing or {}, ensure_ascii=False)[:8000],
        },
        user_id=user_id,
        api_key=key,
        timeout_s=300.0,
    )
    text = outputs.get("text") if isinstance(outputs, dict) else None
    if not text and isinstance(outputs, dict):
        # 兜底取第一个字符串输出
        text = next((v for v in outputs.values() if isinstance(v, str)), "")
    return _normalize(_parse_json_obj(text or ""))


async def ocr_file_bytes(content: bytes, filename: str, user_id: str) -> str:
    """上传 PDF/OFD 字节经 OCR 工作流取全文（自动录入：先识别再抽取）。"""
    key = settings.DIFY_OCR_WORKFLOW_KEY
    if not key:
        raise ValidationException(message="未配置 OCR 工作流（DIFY_OCR_WORKFLOW_KEY）")
    file_id = await dify_service.upload_file(content, filename, user_id, key)
    outputs = await dify_service.run_workflow(
        inputs={
            "file": {
                "transfer_method": "local_file",
                "upload_file_id": file_id,
                "type": "document",
            }
        },
        user_id=user_id,
        api_key=key,
        timeout_s=600.0,
    )
    if isinstance(outputs, dict):
        text = outputs.get("text")
        if not text:
            text = next((v for v in outputs.values() if isinstance(v, str)), "")
        return text or ""
    return ""
