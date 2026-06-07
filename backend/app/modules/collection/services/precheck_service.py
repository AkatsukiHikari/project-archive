"""
四性预检闸门（接收前自动质检）。

依据 DA/T「档案四性」对一批移交明细做确定性评分：
  - 真实性 (authenticity)：来源可溯（责任者/文件日期/移交经办人齐备）
  - 完整性 (integrity)：必填齐全（题名/年度）、申报数与实交数一致
  - 可用性 (usability)：年度为有效数字、文件日期格式规范
  - 安全性 (safety)：密级 / 保管期限取值合规

总分 = 各维度加权和；低于阈值自动拦截人工接收（precheck_passed=False）。
纯函数实现，无外部依赖，可在接收前任意次预演。
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# 合规取值（与 repo_archive 模型保持一致）
_VALID_MJ = {"public", "internal", "confidential", "secret"}
_VALID_BGQX = {"permanent", "long", "short"}

# 维度权重（合计 1.0）
_WEIGHTS = {
    "authenticity": 0.20,
    "integrity": 0.35,
    "usability": 0.25,
    "safety": 0.20,
}
_LABELS = {
    "authenticity": "真实性",
    "integrity": "完整性",
    "usability": "可用性",
    "safety": "安全性",
}

# 闸门阈值：低于此分自动拦截
DEFAULT_THRESHOLD = 60.0


@dataclass(frozen=True)
class EntryInput:
    """单条移交明细的预检输入（来源于 TransferEntry / 草稿明细）。"""
    row_no: int
    TM: Optional[str] = None
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None
    YS: Optional[int] = None
    MJ: Optional[str] = None
    BGQX: Optional[str] = None


@dataclass(frozen=True)
class EntryResult:
    row_no: int
    status: str            # ok | warning | error
    issues: list[str]


@dataclass(frozen=True)
class DimensionResult:
    key: str
    label: str
    score: float           # 0-100
    weight: float
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PrecheckResult:
    score: float
    passed: bool
    threshold: float
    total: int
    ok: int
    warning: int
    error: int
    dimensions: list[DimensionResult]
    entries: list[EntryResult]

    def to_detail(self) -> dict:
        """序列化为可存入 precheck_detail(JSONB) 的字典。"""
        return {
            "score": round(self.score, 1),
            "passed": self.passed,
            "threshold": self.threshold,
            "total": self.total,
            "ok": self.ok,
            "warning": self.warning,
            "error": self.error,
            "dimensions": [
                {
                    "key": d.key,
                    "label": d.label,
                    "score": round(d.score, 1),
                    "weight": d.weight,
                    "issues": d.issues,
                }
                for d in self.dimensions
            ],
        }


def _is_valid_wjrq(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def _ratio(passing: int, total: int) -> float:
    return 100.0 if total == 0 else round(passing / total * 100, 2)


def precheck_entries(
    entries: list[EntryInput],
    expected_count: int,
    handover_person: Optional[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> PrecheckResult:
    """对一批明细执行四性预检，返回总分、维度明细与逐条结果。"""
    total = len(entries)

    # ── 逐条问题归集 ──────────────────────────────────────────────
    entry_results: list[EntryResult] = []
    # 维度命中计数
    auth_pass = integ_pass = usab_pass = safe_pass = 0
    dim_issues: dict[str, list[str]] = {k: [] for k in _WEIGHTS}

    for e in entries:
        issues: list[str] = []
        has_error = False

        # 完整性：题名 + 年度
        if not (e.TM or "").strip():
            issues.append("题名(TM)缺失")
            has_error = True
        if e.ND is None:
            issues.append("年度(ND)缺失")
            has_error = True
        if (e.TM or "").strip() and e.ND is not None:
            integ_pass += 1

        # 真实性：责任者 + 文件日期
        if (e.RZZ or "").strip() and (e.WJRQ or "").strip():
            auth_pass += 1
        else:
            if not (e.RZZ or "").strip():
                issues.append("责任者(RZZ)缺失，来源可溯性不足")
            if not (e.WJRQ or "").strip():
                issues.append("文件日期(WJRQ)缺失")

        # 可用性：年度有效 + 文件日期格式
        nd_ok = e.ND is not None and 1900 <= e.ND <= date.today().year + 1
        wjrq_ok = _is_valid_wjrq(e.WJRQ)
        if nd_ok and wjrq_ok:
            usab_pass += 1
        else:
            if e.ND is not None and not nd_ok:
                issues.append(f"年度({e.ND})超出合理范围")
            if (e.WJRQ or "").strip() and not wjrq_ok:
                issues.append("文件日期格式非法（应为 YYYY-MM-DD）")

        # 安全性：密级 + 保管期限合规
        mj_ok = (e.MJ or "public") in _VALID_MJ
        bgqx_ok = (e.BGQX or "permanent") in _VALID_BGQX
        if mj_ok and bgqx_ok:
            safe_pass += 1
        else:
            if not mj_ok:
                issues.append(f"密级取值非法: {e.MJ}")
            if not bgqx_ok:
                issues.append(f"保管期限取值非法: {e.BGQX}")

        status = "error" if has_error else ("warning" if issues else "ok")
        entry_results.append(EntryResult(row_no=e.row_no, status=status, issues=issues))

    # ── 维度评分 ──────────────────────────────────────────────────
    auth_score = _ratio(auth_pass, total)
    integ_score = _ratio(integ_pass, total)
    usab_score = _ratio(usab_pass, total)
    safe_score = _ratio(safe_pass, total)

    # 真实性额外校验：移交经办人
    if not (handover_person or "").strip():
        auth_score = max(0.0, auth_score - 20)
        dim_issues["authenticity"].append("移交经办人缺失")

    # 完整性额外校验：申报数 vs 实交数
    if expected_count and expected_count != total:
        diff_penalty = min(40.0, abs(expected_count - total) / max(expected_count, 1) * 100)
        integ_score = max(0.0, integ_score - diff_penalty)
        dim_issues["integrity"].append(
            f"申报{expected_count}件，实交{total}件，数量不一致"
        )

    dim_scores = {
        "authenticity": auth_score,
        "integrity": integ_score,
        "usability": usab_score,
        "safety": safe_score,
    }
    dimensions = [
        DimensionResult(
            key=k, label=_LABELS[k], score=dim_scores[k],
            weight=_WEIGHTS[k], issues=dim_issues[k],
        )
        for k in _WEIGHTS
    ]

    overall = sum(dim_scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
    ok = sum(1 for r in entry_results if r.status == "ok")
    warning = sum(1 for r in entry_results if r.status == "warning")
    error = sum(1 for r in entry_results if r.status == "error")

    # 闸门：总分达标 且 无 error 明细
    passed = overall >= threshold and error == 0

    return PrecheckResult(
        score=overall,
        passed=passed,
        threshold=threshold,
        total=total,
        ok=ok,
        warning=warning,
        error=error,
        dimensions=dimensions,
        entries=entry_results,
    )
