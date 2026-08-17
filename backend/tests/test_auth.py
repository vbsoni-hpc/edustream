import pytest
from backend.auth import hash_password, verify_password, create_access_token, verify_access_token

def test_hash_and_verify_password():
    password = "secret_password123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_create_and_verify_access_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    
    user_id = 1
    username = "testuser"
    
    token = create_access_token(user_id, username)
    assert token is not None
    
    decoded = verify_access_token(token)
    assert decoded is not None
    assert decoded["user_id"] == user_id
    assert decoded["username"] == username
    
def test_verify_access_token_invalid():
    assert verify_access_token("invalid_token") is None
