"""
OAuth2 请求/响应 Schema
"""

from pydantic import BaseModel


class AuthorizeRequest(BaseModel):
    """GET /oauth/authorize 查询参数"""
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str = "S256"
    state: str | None = None


class TokenRequest(BaseModel):
    """POST /oauth/token 请求体"""
    grant_type: str  # "authorization_code" or "refresh_token"
    code: str | None = None
    code_verifier: str | None = None
    client_id: str
    redirect_uri: str | None = None
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class LoginForm(BaseModel):
    """登录表单"""
    username: str
    password: str
