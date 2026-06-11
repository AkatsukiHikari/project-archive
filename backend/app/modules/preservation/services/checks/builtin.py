"""内置检测项：DA/T 70-2018《文书类电子档案检测一般要求》四性 45 项指标。

真实性16 / 完整性11 / 可用性9 / 安全性9。
rule 类在此注册自动实现；ai / manual 类仅声明，引擎按 exec_type 转待办。
"""
from __future__ import annotations

import hashlib
import re
from datetime import date

from app.modules.preservation.services.checks.registry import (
    CheckContext, register_check, ok, warn, fail, skip,
)


def _detect_format(data: bytes) -> str | None:
    """按文件头(magic bytes)识别真实格式。"""
    if not data:
        return None
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:2] in (b"II", b"MM"):
        return "tiff"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"PK":
        return "ofd"   # OFD/zip 封装
    head = data[:64].lstrip()
    if head[:5] == b"<?xml" or head[:1] == b"<":
        return "xml"
    return None


_FMT_FAMILY = {"pdf": "pdf", "pdfa": "pdf", "tiff": "tiff", "tif": "tiff", "jpeg": "jpeg", "jpg": "jpeg", "png": "png", "ofd": "ofd", "xml": "xml"}

_STD = "DA/T 70-2018"
_DEFAULT_FORMATS = ["pdf", "pdfa", "ofd", "tiff", "tif", "jpeg", "jpg", "png", "xml"]
_VALID_MJ = {"public", "internal", "secret", "confidential", "top_secret"}


def _all_atts_have(ctx: CheckContext, key: str) -> list[str]:
    return [x.get("original_name") or "?" for x in ctx.attachments if not x.get(key)]


# ── 真实性 rule ───────────────────────────────────────────────────────────────

@register_check("a01_meta_real")
def a01(ctx: CheckContext, p: dict):
    miss = [{"RZZ": "责任者", "WJRQ": "文件日期"}[k] for k in ("RZZ", "WJRQ") if not (ctx.archive.get(k) or "")]
    return fail(f"真实性元数据缺失：{'、'.join(miss)}", missing=miss) if miss else ok("真实性元数据齐全")


@register_check("a03_filename")
def a03(ctx: CheckContext, p: dict):
    if not ctx.attachments:
        return skip("无原文")
    miss = [i + 1 for i, x in enumerate(ctx.attachments) if not (x.get("original_name") or "").strip()]
    return fail(f"{len(miss)} 个原文缺文件名", index=miss) if miss else ok("文件名称规范")


@register_check("a05_responsible")
def a05(ctx: CheckContext, p: dict):
    return ok("责任者已著录") if (ctx.archive.get("RZZ") or "") else fail("责任者缺失，来源不可溯")


@register_check("a06_form_time")
def a06(ctx: CheckContext, p: dict):
    wjrq = (ctx.archive.get("WJRQ") or "").strip()
    if not wjrq:
        return fail("文件日期缺失")
    try:
        date.fromisoformat(wjrq[:10])
        return ok("文件形成时间合规")
    except ValueError:
        return fail(f"文件日期格式非法：{wjrq}")


@register_check("a15_fixity")
def a15(ctx: CheckContext, p: dict):
    if not ctx.attachments:
        return skip("无原文")
    miss = _all_atts_have(ctx, "sha256_hash")
    return fail(f"{len(miss)} 个原文未固化(无SHA256)", files=miss) if miss else ok("真实性固化值已固定")


# ── 完整性 rule ───────────────────────────────────────────────────────────────

@register_check("i01_body_exists")
def i01(ctx: CheckContext, p: dict):
    return ok(f"原文 {len(ctx.attachments)} 件") if ctx.attachments else fail("缺少正文原文")


@register_check("i03_meta_complete")
def i03(ctx: CheckContext, p: dict):
    req = p.get("fields") or ["TM", "ND", "DH"]
    miss = [f for f in req if ctx.archive.get(f) in (None, "", 0)]
    return fail(f"必填元数据缺失：{'、'.join(miss)}", missing=miss) if miss else ok("完整性元数据齐全")


@register_check("i07_page_complete")
def i07(ctx: CheckContext, p: dict):
    if not ctx.attachments:
        return skip("无原文")
    miss = _all_atts_have(ctx, "page_count")
    return warn(f"{len(miss)} 个原文未登记页数，无法核验缺页", files=miss) if miss else ok("页数完整")


@register_check("i09_dh_mapping")
def i09(ctx: CheckContext, p: dict):
    return ok("档号与著录对应") if (ctx.archive.get("DH") or "") else fail("档号缺失，无法与著录一一对应")


@register_check("i11_not_corrupted")
def i11(ctx: CheckContext, p: dict):
    """真校验：下载原文重算 SHA256 与固化值比对，检出篡改/损坏。"""
    if not ctx.attachments:
        return skip("无原文")
    tampered, unverifiable, verified = [], [], 0
    for x in ctx.attachments:
        name = x.get("original_name") or "?"
        data, stored = x.get("data"), x.get("sha256_hash")
        if not data or not stored:
            unverifiable.append(name)
            continue
        actual = hashlib.sha256(data).hexdigest()
        if actual.lower() != str(stored).lower():
            tampered.append({"file": name, "stored": str(stored)[:16], "actual": actual[:16]})
        else:
            verified += 1
    if tampered:
        return fail(f"{len(tampered)} 个原文校验值不符，疑似被篡改/损坏", tampered=tampered)
    if unverifiable and verified == 0:
        return warn(f"{len(unverifiable)} 个原文缺字节或固化值，无法核验", files=unverifiable)
    return ok(f"已重算校验 {verified} 件，数据未被篡改", verified=verified, unverifiable=unverifiable)


# ── 可用性 rule ───────────────────────────────────────────────────────────────

@register_check("u01_format")
def u01(ctx: CheckContext, p: dict):
    """真校验：白名单 + 文件头实测格式与声明是否一致。"""
    allowed = [s.lower() for s in (p.get("formats") or _DEFAULT_FORMATS)]
    if not ctx.attachments:
        return skip("无原文")
    bad, mismatch = [], []
    for x in ctx.attachments:
        name = x.get("original_name") or "?"
        declared = (x.get("file_format") or "").lower()
        if declared not in allowed:
            bad.append((name, declared))
            continue
        real = _detect_format(x.get("data") or b"")
        if real and _FMT_FAMILY.get(declared) and real != _FMT_FAMILY.get(declared):
            mismatch.append({"file": name, "declared": declared, "real": real})
    if bad:
        return fail(f"{len(bad)} 个原文格式不在长期保存白名单", bad=bad)
    if mismatch:
        return fail(f"{len(mismatch)} 个原文实际格式与声明不符", mismatch=mismatch)
    return ok("格式合规且文件头一致")


@register_check("u03_openable")
def u03(ctx: CheckContext, p: dict):
    """真校验：按文件头判断能否被识别/打开。"""
    if not ctx.attachments:
        return skip("无原文")
    bad = []
    for x in ctx.attachments:
        data = x.get("data")
        if not data:
            bad.append({"file": x.get("original_name") or "?", "reason": "无字节"})
        elif _detect_format(data) is None:
            bad.append({"file": x.get("original_name") or "?", "reason": "文件头无法识别"})
    return fail(f"{len(bad)} 个原文无法正常打开", bad=bad) if bad else ok("原文均可正常打开")


@register_check("u07_searchable")
def u07(ctx: CheckContext, p: dict):
    miss = [f for f in ("TM", "DH") if not (ctx.archive.get(f) or "")]
    return fail(f"检索关键字段缺失：{'、'.join(miss)}", missing=miss) if miss else ok("题名、档号可检索定位")


@register_check("u09_naming_locate")
def u09(ctx: CheckContext, p: dict):
    dh = ctx.archive.get("DH") or ""
    pat = p.get("pattern")
    if not dh:
        return fail("档号为空，无法定位")
    if pat and not re.match(pat, dh):
        return warn(f"档号 {dh} 不符合编号规则")
    return ok("命名/编号可定位")


# ── 安全性 rule ───────────────────────────────────────────────────────────────

@register_check("s01_tamper_proof")
def s01(ctx: CheckContext, p: dict):
    if not ctx.attachments:
        return skip("无原文")
    miss = _all_atts_have(ctx, "sha256_hash")
    return fail(f"{len(miss)} 个原文无防篡改固化值", files=miss) if miss else ok("已固化，具备防篡改能力")


@register_check("s07_mj_label")
def s07(ctx: CheckContext, p: dict):
    mj = ctx.archive.get("MJ")
    if not mj:
        return fail("未标注密级")
    return ok("密级标注合规") if mj in _VALID_MJ else fail(f"密级取值非法：{mj}")


# ══ 全量目录声明（45 项，DA/T 70-2018） ══════════════════════════════════════
def _it(code, name, dim, exec_type, weight=10, blocking=False, params=None, std=_STD):
    return {"code": code, "name": name, "dimension": dim, "exec_type": exec_type,
            "standard_ref": std, "default_weight": weight, "default_blocking": blocking,
            "default_params": params, "carrier_type": "electronic"}


CATALOG: list[dict] = [
    # ── 真实性 16 ──
    _it("a01_meta_real", "真实性元数据齐全", "authenticity", "rule", 15, True),
    _it("a02_meta_compliance", "元数据合规性", "authenticity", "manual", 8),
    _it("a03_filename", "文件名称规范性", "authenticity", "rule", 8),
    _it("a04_source_legality", "形成单位(来源)合法性", "authenticity", "manual", 10),
    _it("a05_responsible", "责任者一致性", "authenticity", "rule", 8),
    _it("a06_form_time", "文件形成时间合规", "authenticity", "rule", 8),
    _it("a07_doc_no", "发文字号检测", "authenticity", "manual", 6),
    _it("a08_content_meta_consistency", "内容与元数据属性一致性", "authenticity", "ai", 10),
    _it("a09_format_declared", "文件格式与声明一致性", "authenticity", "manual", 6),
    _it("a10_version", "稿本/版本标识检测", "authenticity", "manual", 6),
    _it("a11_esign", "电子签名有效性", "authenticity", "manual", 12, True),
    _it("a12_eseal", "电子印章有效性", "authenticity", "manual", 10),
    _it("a13_timestamp", "可信时间戳检测", "authenticity", "manual", 8),
    _it("a14_binding", "元数据—内容—签名关联绑定未篡改", "authenticity", "manual", 12),
    _it("a15_fixity", "真实性固化值(数字摘要)一致", "authenticity", "rule", 12, True),
    _it("a16_transfer_log", "移交/交接登记信息检测", "authenticity", "manual", 6),
    # ── 完整性 11 ──
    _it("i01_body_exists", "正文原文存在性", "integrity", "rule", 15, True),
    _it("i02_attachment_complete", "附件齐全性", "integrity", "manual", 8),
    _it("i03_meta_complete", "完整性元数据项齐全", "integrity", "rule", 15, True,
        {"fields": ["TM", "ND", "DH"]}),
    _it("i04_aip_structure", "AIP 归档信息包结构/目录层级合规", "integrity", "manual", 10),
    _it("i05_package", "打包封装格式合规", "integrity", "manual", 8),
    _it("i06_count_match", "文件数量与著录份数一致", "integrity", "manual", 8),
    _it("i07_page_complete", "页数完整(缺页检测)", "integrity", "rule", 8),
    _it("i08_doc_entry_map", "文档—条目对应完整", "integrity", "manual", 8),
    _it("i09_dh_mapping", "档号与著录一一对应", "integrity", "rule", 10),
    _it("i10_body_attach_relation", "正文与附件关联完整", "integrity", "manual", 6),
    _it("i11_not_corrupted", "数据未破坏/变异/丢失(校验值)", "integrity", "rule", 12, True),
    # ── 可用性 9 ──
    _it("u01_format", "长期保存格式合规(PDF/A·OFD·TIFF)", "usability", "rule", 12, True,
        {"formats": _DEFAULT_FORMATS}),
    _it("u02_format_version", "格式版本合规", "usability", "manual", 6),
    _it("u03_openable", "文件可正常打开", "usability", "rule", 10),
    _it("u04_render", "内容正确呈现(文字/图像/排版)", "usability", "ai", 10),
    _it("u05_font", "字体嵌入/缺字检测", "usability", "ai", 6),
    _it("u06_image_quality", "图像清晰度/分辨率达标", "usability", "ai", 8),
    _it("u07_searchable", "元数据字段可检索定位", "usability", "rule", 8),
    _it("u08_printable", "可正常输出/打印", "usability", "manual", 6),
    _it("u09_naming_locate", "命名/编号支持定位", "usability", "rule", 6),
    # ── 安全性 9 ──
    _it("s01_tamper_proof", "防篡改措施(校验值/签名)", "safety", "rule", 12, True),
    _it("s02_access_control", "防非法修改/删除权限控制", "safety", "manual", 10),
    _it("s03_virus", "病毒/恶意代码检测", "safety", "manual", 12, True),
    _it("s04_package_scan", "归档数据包安全扫描", "safety", "manual", 8),
    _it("s05_encryption", "涉密档案加密措施", "safety", "manual", 8),
    _it("s06_access_right", "用户访问权限合规", "safety", "manual", 8),
    _it("s07_mj_label", "密级标注合规", "safety", "rule", 8),
    _it("s08_storage_safety", "存储/载体安全", "safety", "manual", 6),
    _it("s09_backup", "备份策略检测", "safety", "manual", 6),
]
