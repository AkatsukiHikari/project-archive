import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配。"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """对明文密码进行 bcrypt 哈希，返回哈希字符串。"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")
