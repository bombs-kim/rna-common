"""
Basic tests for HTTP endpoints in server.http.
Project existence is determined by DB rows; tests use a test DB and fixtures.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from resource_based_modules.project.models import Project
from server import app

client = TestClient(app)


class TestReadProjects:
    def test_empty_when_no_projects(self):
        r = client.get("/api/projects")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert "itemsPerPage" in data

    def test_returns_sorted_projects(self, db_session):
        db_session.add_all(
            [
                Project(container_name="project-1-1"),
                Project(container_name="project-1-2"),
                Project(container_name="project-1-3"),
            ]
        )
        db_session.commit()
        r = client.get("/api/projects")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        ids = [p["id"] for p in data["items"]]
        assert ids == sorted(ids)
        assert all(
            "id" in p
            and "container_name" in p
            and "created_at" in p
            and "updated_at" in p
            for p in data["items"]
        )


class TestGetProject:
    def test_404_when_project_missing(self):
        r = client.get("/api/projects/99")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_200_when_project_exists(self, db_session):
        p = Project(container_name="project-1-1")
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        r = client.get(f"/api/projects/{p.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == p.id
        assert data["container_name"] == "project-1-1"
        assert "created_at" in data and "updated_at" in data


class TestReadProjectCode:
    def test_404_when_project_missing(self):
        r = client.get("/api/projects/99/code")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_200_with_empty_content_when_file_missing(self, db_session, tmp_path):
        p = Project(container_name=None)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        with patch("server.http.settings.PROJECT_CONTAINERS_DIR", tmp_path):
            r = client.get(f"/api/projects/{p.id}/code")
        assert r.status_code == 200
        data = r.json()
        assert data["content"] == ""
        assert data["functions"] == []

    def test_200_when_file_exists(self, db_session, tmp_path):
        p = Project(container_name=None)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        (tmp_path / "1" / str(p.id) / "data").mkdir(parents=True)
        (tmp_path / "1" / str(p.id) / "data" / "main.py").write_text("print(1)")
        with patch("server.http.settings.PROJECT_CONTAINERS_DIR", tmp_path):
            r = client.get(f"/api/projects/{p.id}/code")
        assert r.status_code == 200
        data = r.json()
        assert data["content"] == "print(1)"
        assert "functions" in data


class TestOverwriteCode:
    def test_404_when_project_missing(self):
        r = client.put("/api/projects/99/code", json={"code": "x = 1"})
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()


class TestRunAgent:
    def test_404_when_project_missing(self):
        r = client.post("/api/projects/99/run_agent", json={"prompt": "hello"})
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_200_returns_task_id_and_pending(self, db_session):
        p = Project(container_name="project-1-1")
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        r = client.post(
            f"/api/projects/{p.id}/run_agent",
            json={"prompt": "hello"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert "message" in data
