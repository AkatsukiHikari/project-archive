"""四性检测项注册表与上下文。

每个 rule 类检测项 = 注册到 CHECK_REGISTRY 的一个纯函数 (ctx, params) -> CheckOutcome。
加新规则条款 = 加一个被 @register_check 装饰的函数，引擎无需改动。
ai / manual 类不在此注册(由引擎按 exec_type 处理)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class CheckContext:
    """检测对象快照：档案元数据 + 原文附件元信息。"""
    archive: dict                      # TM/RZZ/ND/DH/QZH/MJ/WJRQ/YS/ext_fields...
    attachments: list[dict] = field(default_factory=list)  # file_format/sha256_hash/page_count/file_size/original_name
    ocr_text: Optional[str] = None     # AI 类检测项用（OCR 全文，可空）


@dataclass(frozen=True)
class CheckOutcome:
    result: str                        # pass | warn | fail | skip
    message: str = ""
    evidence: dict = field(default_factory=dict)
    confidence: Optional[float] = None

    @property
    def score(self) -> Optional[float]:
        return {"pass": 100.0, "warn": 60.0, "fail": 0.0}.get(self.result)  # skip -> None（不计分）


CheckFn = Callable[[CheckContext, dict], CheckOutcome]
CHECK_REGISTRY: dict[str, CheckFn] = {}


def register_check(code: str) -> Callable[[CheckFn], CheckFn]:
    def deco(fn: CheckFn) -> CheckFn:
        CHECK_REGISTRY[code] = fn
        return fn
    return deco


# 便捷构造
def ok(msg: str = "通过", **ev) -> CheckOutcome:
    return CheckOutcome(result="pass", message=msg, evidence=ev)


def warn(msg: str, **ev) -> CheckOutcome:
    return CheckOutcome(result="warn", message=msg, evidence=ev)


def fail(msg: str, **ev) -> CheckOutcome:
    return CheckOutcome(result="fail", message=msg, evidence=ev)


def skip(msg: str = "不适用", **ev) -> CheckOutcome:
    return CheckOutcome(result="skip", message=msg, evidence=ev)
