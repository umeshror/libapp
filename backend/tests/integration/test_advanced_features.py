from fastapi.testclient import TestClient
from app.main import app
import pytest


def test_pagination(client):
    # Seed 25 books
    for i in range(25):
        client.post(
            "/books/",
            json={
                "title": f"Book {i}",
                "author": "Auth",
                "isbn": f"PAG{i}",
                "total_copies": 1,
                "available_copies": 1,
            },
        )

    # Page 1 (limit 20, offset 0)
    response = client.get("/books/?limit=20&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 20
    assert data["meta"]["total"] >= 25
    assert data["meta"]["limit"] == 20
    assert data["meta"]["offset"] == 0
    assert data["meta"]["has_more"] is True

    # Page 2 (limit 20, offset 20)
    response = client.get("/books/?limit=20&offset=20")
    assert response.status_code == 200
    data = response.json()
    assert (
        len(data["data"]) == 5
    )  # Remaining 5 (assuming exactly 25 if DB was empty, or >= 5)
    # Fixture teardown ensures clean state between tests

    # Check meta has_more
    assert data["meta"]["has_more"] is False


def test_search(client):
    # Seed specific books
    client.post(
        "/books/",
        json={
            "title": "Unique Python Guide",
            "author": "Guido",
            "isbn": "PY1",
            "total_copies": 1,
        },
    )
    client.post(
        "/books/",
        json={
            "title": "Rust Programming",
            "author": "Steve",
            "isbn": "RS1",
            "total_copies": 1,
        },
    )

    # Search "Python"
    response = client.get("/books/?q=Python")
    assert response.status_code == 200
    data = response.json()
    items = data["data"]
    assert len(items) == 1
    assert items[0]["title"] == "Unique Python Guide"

    # Search "steve" (case insensitive author)
    response = client.get("/books/?q=steve")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["title"] == "Rust Programming"


def test_sorting(client):
    # A, B, C titles
    client.post(
        "/books/",
        json={"title": "Aalpha", "author": "X", "isbn": "S1", "total_copies": 1},
    )
    client.post(
        "/books/",
        json={"title": "Ccharlie", "author": "X", "isbn": "S2", "total_copies": 1},
    )
    client.post(
        "/books/",
        json={"title": "Bbravo", "author": "X", "isbn": "S3", "total_copies": 1},
    )

    # Sort A-Z
    response = client.get("/books/?sort=title&q=X")  # Filter by author X to avoid noise
    assert response.status_code == 200
    items = response.json()["data"]

    # We filter manually just in case
    filtered_items = [b for b in items if b["author"] == "X"]
    # Sorting by title ASC
    assert filtered_items[0]["title"] == "Aalpha"
    assert filtered_items[1]["title"] == "Bbravo"
    assert filtered_items[2]["title"] == "Ccharlie"

    # Sort Z-A
    response = client.get("/books/?sort=-title&q=X")
    assert response.status_code == 200
    items = response.json()["data"]
    filtered_items = [b for b in items if b["author"] == "X"]
    assert filtered_items[0]["title"] == "Ccharlie"
    assert filtered_items[1]["title"] == "Bbravo"
    assert filtered_items[2]["title"] == "Aalpha"


def test_invalid_params(client):
    response = client.get("/books/?sort=invalid_field")
    assert response.status_code == 400
