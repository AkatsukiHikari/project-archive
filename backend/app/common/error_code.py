"""
统一错误码常量

命名规则：
- 0         : 成功
- 1000-1099 : 认证 / 授权
- 1100-1199 : 用户 / IAM
- 2000-2099 : 资源收集 (Collection)
- 3000-3099 : 档案管理 (Repository)
- 4000-4099 : 四性检测 (Preservation)
- 5000-5099 : 利用服务 (Utilization)
- 6000-6099 : AI 模块 (AI Agent / Patch / Eval)
- 9000-9099 : 参数校验
- 9999      : 系统内部错误
"""


class ErrorCode:
    # ── 成功 ──
    SUCCESS = 0

    # ── 通用 ──
    NOT_FOUND = 404

    # ── 认证 / 授权 (1000-1099) ──
    NOT_AUTHENTICATED = 1000
    TOKEN_EXPIRED = 1001
    PERMISSION_DENIED = 1002
    INVALID_TOKEN = 1003

    # ── 用户 / IAM (1100-1199) ──
    USERNAME_EXISTS = 1100
    USER_NOT_FOUND = 1101
    PASSWORD_ERROR = 1102
    USER_INACTIVE = 1103
    EMAIL_EXISTS = 1104
    INVALID_PASSWORD = 1105

    # ── 资源收集 (2000-2099) ──
    FILE_FORMAT_UNSUPPORTED = 2000
    FILE_TOO_LARGE = 2001
    SIP_PARSE_ERROR = 2002

    # ── 档案管理 (3000-3099) ──
    ARCHIVE_NOT_FOUND = 3000
    FONDS_NOT_FOUND = 3001
    ARCHIVE_FILE_NOT_FOUND = 3002
    ARCHIVE_ITEM_NOT_FOUND = 3003
    ARCHIVE_NO_RULE_NOT_FOUND = 3004
    FONDS_CODE_EXISTS = 3010

    # ── 四性检测 (4000-4099) ──
    INTEGRITY_CHECK_FAILED = 4000
    AUTHENTICITY_CHECK_FAILED = 4001
    USABILITY_CHECK_FAILED = 4002
    SAFETY_CHECK_FAILED = 4003

    # ── 利用服务 (5000-5099) ──
    SEARCH_ERROR = 5000

    # ── AI 模块 (6000-6099) ──
    AI_MODEL_UNAVAILABLE = 6001          # 上游模型不可用 / 超时
    AI_RETRIEVAL_FORBIDDEN = 6002        # 检索越权（tenant/密级/类目越界）
    AI_PATCH_STATE_CONFLICT = 6003       # Patch 状态冲突（已被处理）
    AI_EVAL_BLOCKED = 6004               # Eval 未达标，Workflow 上线被阻
    AI_CITATION_INVALID = 6005           # 引用校验失败（chunk 不存在或越权）
    AI_WORKFLOW_VERSION_MISMATCH = 6006  # Workflow 版本不一致
    AI_TOOL_AUTH_FAILED = 6007           # Tool 鉴权失败（X-User-Token 缺失/过期）
    AI_CAPABILITY_DISABLED = 6008        # 场景未启用 / 灰度未放开
    AI_QUOTA_EXCEEDED = 6009             # 租户 AI 配额超限

    # ── 参数校验 (9000-9099) ──
    VALIDATION_ERROR = 9000
    MISSING_PARAMETER = 9001

    # ── 系统内部错误 ──
    INTERNAL_ERROR = 9999
