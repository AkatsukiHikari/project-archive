"""
密码工具函数单元测试
"""

import pytest
from app.core.security.password import get_password_hash, verify_password


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        """哈希后的密码不应与明文相同"""
        plain = "MySecret123!"
        hashed = get_password_hash(plain)
        assert hashed != plain

    def test_verify_correct_password(self):
        """正确密码校验通过"""
        plain = "MySecret123!"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        """错误密码校验失败"""
        hashed = get_password_hash("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_same_password_different_hash(self):
        """相同密码每次哈希结果不同（bcrypt salt）"""
        plain = "SamePassword"
        hash1 = get_password_hash(plain)
        hash2 = get_password_hash(plain)
        assert hash1 != hash2
        # 但两者都能校验通过
        assert verify_password(plain, hash1)
        assert verify_password(plain, hash2)
