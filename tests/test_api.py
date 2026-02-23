import sys
import os

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_docs_endpoint():
    response = client.get("/docs")
    assert response.status_code == 200


def test_create_policy():
    response = client.post(
        "/policies",
        json={
            "policy_id": "TEST-POLICY-1",
            "conditions": [
                {
                    "field": "destination_port",
                    "operator": "==",
                    "value": "443"
                }
            ],
            "action": "block"
        }
    )

    assert response.status_code in (200, 201, 409)


def test_submit_connection():
    response = client.post(
        "/connections",
        json={
            "source_ip": "192.168.1.10",
            "destination_ip": "10.0.0.5",
            "destination_port": 80,
            "protocol": "TCP",
            "timestamp": "2025-01-01T00:00:00Z"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "connection_id" in data
    assert "decision" in data

