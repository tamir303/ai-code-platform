"""
Integration tests for the health check endpoint.
"""
import pytest


pytestmark = pytest.mark.integration


class TestHealthCheck:
    async def test_health_returns_ok(self, client):
        """GET /health returns healthy status."""
        resp = await client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "HEALTHY"
        assert "env" in data

    async def test_health_available(self, client):
        """Health endpoint reports the running environment."""
        resp = await client.get("/health")

        assert resp.status_code == 200
