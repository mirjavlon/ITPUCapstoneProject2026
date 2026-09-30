"""Unit tests for utility and service modules."""

from datetime import timedelta

import pytest

from app.models.user import AccountType
from app.utils.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


# =====================================================================
# Password hashing
# =====================================================================

class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = get_password_hash("mypassword")
        assert verify_password("mypassword", hashed)

    def test_wrong_password_rejected(self):
        hashed = get_password_hash("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_rejects_over_72_bytes(self):
        with pytest.raises(ValueError, match="72"):
            get_password_hash("a" * 73)

    def test_verify_handles_corrupt_hash(self):
        assert not verify_password("password", "not-a-real-hash")


# =====================================================================
# JWT tokens
# =====================================================================

class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(42, expires_delta=timedelta(minutes=5))
        assert decode_access_token(token) == 42

    def test_expired_token_returns_none(self):
        token = create_access_token(1, expires_delta=timedelta(seconds=-1))
        assert decode_access_token(token) is None

    def test_invalid_token_returns_none(self):
        assert decode_access_token("garbage.token.value") is None

    def test_empty_token_returns_none(self):
        assert decode_access_token("") is None


# =====================================================================
# AccountType enum
# =====================================================================

class TestAccountType:
    def test_organizer_value(self):
        assert AccountType.ORGANIZER.value == "organizer"

    def test_manager_value(self):
        assert AccountType.MANAGER.value == "manager"

    def test_is_string(self):
        assert isinstance(AccountType.ORGANIZER, str)
