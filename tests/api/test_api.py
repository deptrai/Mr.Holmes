"""tests/api/test_api.py — REST API endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from Core.api.server import app

client = TestClient(app)

class TestHealth:
    def test_health_endpoint(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

class TestAuth:
    def test_login_success(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert r.json()["role"] == "admin"
    
    def test_login_wrong_password(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401
    
    def test_login_unknown_user(self):
        r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
        assert r.status_code == 401
    
    def test_protected_endpoint_no_token(self):
        r = client.get("/api/me")
        assert r.status_code == 403  # No credentials
    
    def test_protected_endpoint_valid_token(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        token = r.json()["access_token"]
        r2 = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.json()["username"] == "admin"
    
    def test_protected_endpoint_invalid_token(self):
        r = client.get("/api/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401

class TestPlugins:
    def _get_token(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        return r.json()["access_token"]
    
    def test_list_plugins(self):
        token = self._get_token()
        r = client.get("/api/plugins", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "plugins" in r.json()
        assert len(r.json()["plugins"]) > 0
    
    def test_list_plugins_no_auth(self):
        r = client.get("/api/plugins")
        assert r.status_code == 403

class TestPluginCheck:
    def _get_token(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        return r.json()["access_token"]
    
    def test_dns_check(self):
        token = self._get_token()
        r = client.post("/api/plugins/check", json={
            "plugin_name": "DNSResolver",
            "target": "example.com",
            "target_type": "domain"
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "is_success" in r.json()
    
    def test_plugin_not_found(self):
        token = self._get_token()
        r = client.post("/api/plugins/check", json={
            "plugin_name": "NonExistent",
            "target": "test",
            "target_type": "username"
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404
