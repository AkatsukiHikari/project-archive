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
- 9000-9099 : 参数校验
- 9999      : 系统内部错误
"""


class ErrorCode:
    # ── 成功 ──
    SUCCESS = 0

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
    FONDS_CODE_EXISTS = 3010

    # ── 四性检测 (4000-4099) ──
    INTEGRITY_CHECK_FAILED = 4000
    AUTHENTICITY_CHECK_FAILED = 4001
    USABILITY_CHECK_FAILED = 4002
    SAFETY_CHECK_FAILED = 4003

    # ── 利用服务 (5000-5099) ──
    SEARCH_ERROR = 5000

    # ── 参数校验 (9000-9099) ──
    VALIDATION_ERROR = 9000
    MISSING_PARAMETER = 9001

    # ── 系统内部错误 ──
    INTERNAL_ERROR = 9999
