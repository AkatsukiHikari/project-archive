from typing import Optional
from pydantic import BaseModel

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
