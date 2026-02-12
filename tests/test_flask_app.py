"""Tests for the Flask application routes."""

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestFlaskRoutes:
    def test_index_page(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_results_page_empty(self, client):
        response = client.get("/results")
        assert response.status_code == 200
        assert b"No results yet" in response.data

    def test_run_agents_redirects(self, client):
        response = client.post("/run")
        assert response.status_code == 302  # redirect to results

    def test_run_agents_then_results(self, client):
        client.post("/run")
        response = client.get("/results")
        assert response.status_code == 200
        assert b"Summary" in response.data

    def test_api_run(self, client):
        response = client.post("/api/run")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_files_processed" in data
        assert "total_events" in data

    def test_view_nonexistent_file(self, client):
        response = client.get("/view/nonexistent.xml")
        assert response.status_code == 200
