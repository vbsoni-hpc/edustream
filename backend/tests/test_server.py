import pytest
import os
from fastapi.testclient import TestClient
from backend.server import app
from backend.models import init_db, create_user
from backend.auth import create_access_token
from config import DB_PATH

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    
    # Create test user
    user_id = create_user("testuser", "hashedpass", "Test User", "Test Inst")
    
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_access_token(1, "testuser")
    return {"Authorization": f"Bearer {token}"}

def test_register(client):
    response = client.post("/api/auth/register", json={
        "username": "newuser",
        "password": "password123",
        "display_name": "New User"
    })
    assert response.status_code == 200
    assert "token" in response.json()

def test_get_users(client, auth_headers):
    response = client.get("/api/users", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert len(data["users"]) >= 1
    
def test_get_users_unauthorized(client):
    response = client.get("/api/users")
    assert response.status_code == 401
