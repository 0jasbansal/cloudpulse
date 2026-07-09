from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_and_get_item():
    create_response = client.post("/items", json={"name": "Test Item", "description": "A test"})
    assert create_response.status_code == 200
    item_id = create_response.json()["id"]

    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Item"


def test_get_nonexistent_item():
    response = client.get("/items/9999")
    assert response.status_code == 404
