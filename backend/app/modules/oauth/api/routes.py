"""
OAuth2 API 路由

端点：
- GET  /oauth/authorize — 授权端点
- GET  /oauth/login     — 登录页（HTML）
- POST /oauth/login     — 提交登录
- POST /oauth/token     — 令牌端点
- POST /oauth/logout    — 注销
"""

from urllib.parse import urlencode, quote

from fastapi import APIRouter, Request, Response, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.modules.oauth.services import oauth_service
from app.modules.oauth.session import create_session, get_session, delete_session
from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.repositories.iam_repository import SQLAlchemyIAMRepository
from app.infra.db.session import AsyncSessionLocal
from app.infra.cache.redis import redis_service
from app.common.response import success, fail
from app.common.error_code import ErrorCode

import os

# 登录限速配置
_LOGIN_FAIL_KEY = "login_fail:{ip}"
_LOGIN_FAIL_MAX = 10          # 最大失败次数
_LOGIN_FAIL_WINDOW = 300      # 计数窗口（秒）
_LOGIN_LOCKOUT_DURATION = 900 # 封禁时长（秒）


async def _check_login_rate_limit(ip: str) -> bool:
    """返回 True 表示允许继续，False 表示已超限"""
    key = _LOGIN_FAIL_KEY.format(ip=ip)
    raw = await redis_service.get(key)
    count = int(raw) if raw else 0
    return count < _LOGIN_FAIL_MAX


async def _record_login_failure(ip: str) -> None:
    key = _LOGIN_FAIL_KEY.format(ip=ip)
    raw = await redis_service.get(key)
    count = int(raw) if raw else 0
    new_count = count + 1
    # 首次失败时设置窗口，超过阈值后延长封禁时长
    ttl = _LOGIN_LOCKOUT_DURATION if new_count >= _LOGIN_FAIL_MAX else _LOGIN_FAIL_WINDOW
    await redis_service.set(key, str(new_count), expire=ttl)


async def _clear_login_failure(ip: str) -> None:
    await redis_service.delete(_LOGIN_FAIL_KEY.format(ip=ip))

router = APIRouter()

# Jinja2 模板目录
_template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=_template_dir)

# Cookie 配置
SESSION_COOKIE = "sams_session"
SESSION_MAX_AGE = 24 * 3600  # 24 小时


# ─── GET /oauth/authorize ───

@router.get("/authorize")
async def authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    response_type: str = Query("code"),
    state: str = Query(None),
):
    """
    OAuth2 授权端点。

    1. 校验 client_id + redirect_uri
    2. 检查 Session Cookie
       - 有 session → 直接签发授权码，重定向回前端
       - 无 session → 重定向到登录页
    """
    # 校验客户端
    oauth_service.validate_client(client_id, redirect_uri)

    # 检查现有 session
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        user_id = await get_session(session_id)
        if user_id:
            # SSO 核心：已登录，自动签发授权码
            code = await oauth_service.create_authorization_code(
                user_id=user_id,
                client_id=client_id,
                redirect_uri=redirect_uri,
                code_challenge=code_challenge,
            )
            params = {"code": code}
            if state:
                params["state"] = state
            return RedirectResponse(
                url=f"{redirect_uri}?{urlencode(params)}",
                status_code=302,
            )

    # 未登录 → 跳转登录页(通过login端点保留所有参数)
    login_params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "response_type": response_type,
        **({"state": state} if state else {}),
    })
    return RedirectResponse(url=f"/oauth/login?{login_params}", status_code=302)


# ─── GET /oauth/login ───

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    client_id: str = Query(""),
    redirect_uri: str = Query(""),
    code_challenge: str = Query(""),
    code_challenge_method: str = Query("S256"),
    response_type: str = Query("code"),
    state: str = Query(None),
    error: str = Query(None),
):
    """渲染 SSO 登录页"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "response_type": response_type,
        "state": state or "",
        "error": error,
    })


# ─── POST /oauth/login ───

@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
    response_type: str = Form("code"),
    state: str = Form(""),
):
    """
    处理登录表单提交：
    1. 验证用户名密码
    2. 创建 SSO Session → Set-Cookie
    3. 签发授权码 → 重定向回前端
    """
    client_ip = request.client.host if request.client else "unknown"

    # 检查 IP 是否被限速封禁
    if not await _check_login_rate_limit(client_ip):
        params = urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "response_type": response_type,
            "state": state,
            "error": "登录尝试次数过多，请 15 分钟后再试",
        })
        return RedirectResponse(url=f"/oauth/login?{params}", status_code=302)

    # 构建 IAM Service 实例
    async with AsyncSessionLocal() as db:
        repo = SQLAlchemyIAMRepository(db)
        iam_service = IAMService(repo)
        user = await iam_service.authenticate(username=username, password=password)

    if not user:
        # 记录失败次数
        await _record_login_failure(client_ip)
        # 登录失败 → 重新显示登录页
        params = urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "response_type": response_type,
            "state": state,
            "error": "用户名或密码错误",
        })
        return RedirectResponse(url=f"/oauth/login?{params}", status_code=302)

    if not user.is_active:
        params = urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "response_type": response_type,
            "state": state,
            "error": "用户已被禁用",
        })
        return RedirectResponse(url=f"/oauth/login?{params}", status_code=302)

    # 登录成功，清除失败计数
    await _clear_login_failure(client_ip)

    # 校验客户端
    oauth_service.validate_client(client_id, redirect_uri)

    # 创建 SSO Session
    session_id = await create_session(str(user.id))

    # 签发授权码
    code = await oauth_service.create_authorization_code(
        user_id=str(user.id),
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
    )

    # 重定向回前端，并设置 session cookie
    params = {"code": code}
    if state:
        params["state"] = state
    response = RedirectResponse(
        url=f"{redirect_uri}?{urlencode(params)}",
        status_code=302,
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/oauth",
        secure=False,  # 开发环境用 HTTP；生产环境改为 True
    )
    return response


# ─── POST /oauth/token ───

@router.post("/token")
async def token_endpoint(
    grant_type: str = Form(...),
    code: str = Form(None),
    code_verifier: str = Form(None),
    client_id: str = Form(...),
    redirect_uri: str = Form(None),
    refresh_token: str = Form(None),
):
    """
    OAuth2 令牌端点：
    - grant_type=authorization_code → 授权码换 token
    - grant_type=refresh_token → 刷新 token
    """
    if grant_type == "authorization_code":
        if not code or not code_verifier or not redirect_uri:
            return fail(ErrorCode.VALIDATION_ERROR, "缺少必要参数: code, code_verifier, redirect_uri")

        tokens = await oauth_service.exchange_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            client_id=client_id,
            redirect_uri=redirect_uri,
        )
        return success(data=tokens)

    elif grant_type == "refresh_token":
        if not refresh_token:
            return fail(ErrorCode.VALIDATION_ERROR, "缺少必要参数: refresh_token")

        tokens = await oauth_service.refresh_access_token(refresh_token)
        return success(data=tokens)

    else:
        return fail(ErrorCode.VALIDATION_ERROR, f"不支持的 grant_type: {grant_type}")


# ─── POST /oauth/logout ───

@router.post("/logout")
async def logout(request: Request, response: Response):
    """SSO 注销：清除 session cookie 和 Redis session"""
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        await delete_session(session_id)

    response.delete_cookie(key=SESSION_COOKIE, path="/oauth")
    return success(message="已注销")
