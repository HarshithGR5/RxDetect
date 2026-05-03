"""
test_api.py
FastAPI integration tests using httpx TestClient.
Uses an in-memory SQLite DB to avoid needing a real Postgres instance.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.dependencies import get_db
from app.models import Base


# ── In-memory SQLite setup ────────────────────────────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(email="test@rx.com", password="SecurePass123"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    return resp.json()["access_token"]


# ── Health check ──────────────────────────────────────────────────────────────

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_register_success():
    resp = client.post("/api/v1/auth/register", json={
        "email": "newuser@rx.com",
        "password": "Pass1234!",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    assert "user_id" in resp.json()


def test_register_duplicate_email():
    payload = {"email": "dup@rx.com", "password": "Pass1234!"}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_success():
    token = _register_and_login()
    assert token is not None and len(token) > 10


def test_login_wrong_password():
    _register_and_login()
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "test@rx.com", "password": "WrongPassword"},
    )
    assert resp.status_code == 401


def test_get_me():
    token = _register_and_login()
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@rx.com"


# ── Patients ──────────────────────────────────────────────────────────────────

def test_create_and_get_patient():
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post("/api/v1/patients/", json={
        "full_name": "Ravi Kumar",
        "age": 45,
        "gender": "Male",
    }, headers=headers)
    assert create_resp.status_code == 201
    pid = create_resp.json()["patient_id"]

    get_resp = client.get(f"/api/v1/patients/{pid}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Ravi Kumar"


def test_list_patients_empty():
    token = _register_and_login(email="empty@rx.com")
    resp = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Prescriptions ─────────────────────────────────────────────────────────────

def test_upload_prescription():
    token = _register_and_login(email="pharmacist@rx.com")
    headers = {"Authorization": f"Bearer {token}"}

    import io
    fake_image = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)  # minimal JPEG bytes
    fake_image.name = "test_rx.jpg"

    resp = client.post(
        "/api/v1/prescriptions/upload",
        files={"file": ("test_rx.jpg", fake_image, "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 201
    assert "prescription_id" in resp.json()


def test_list_prescriptions_authenticated():
    token = _register_and_login(email="listtest@rx.com")
    resp = client.get("/api/v1/prescriptions/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_prescriptions_requires_auth():
    resp = client.get("/api/v1/prescriptions/")
    assert resp.status_code == 401


def test_prescription_not_found():
    token = _register_and_login(email="notfound@rx.com")
    import uuid
    resp = client.get(
        f"/api/v1/prescriptions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404