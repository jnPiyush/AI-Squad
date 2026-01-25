"""
Dashboard tests
"""
import pytest


flask = pytest.importorskip("flask")

from ai_squad.dashboard import create_app


class TestDashboard:
    """Test dashboard routes and API endpoints"""

    def test_dashboard_pages(self, tmp_path):
        app = create_app(workspace_root=tmp_path)
        app.config["TESTING"] = True
        client = app.test_client()

        for path in ("/", "/health", "/work", "/convoys", "/graph", "/delegations"):
            response = client.get(path)
            assert response.status_code == 200

    def test_dashboard_api_endpoints(self, tmp_path):
        app = create_app(workspace_root=tmp_path)
        app.config["TESTING"] = True
        client = app.test_client()

        endpoints = (
            "/api/health",
            "/api/delegations",
            "/api/graph",
            "/api/work",
            "/api/convoys",
            "/api/signals/pm",
            "/api/identity",
            "/api/capabilities",
            "/api/scout",
            "/api/workers",
            "/api/hooks",
        )

        for path in endpoints:
            response = client.get(path)
            assert response.status_code == 200
            payload = response.get_json()
            assert payload is not None
            assert payload.get("success") is True