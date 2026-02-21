from fastapi.testclient import TestClient
from app.main import app
import pytest


def test_api_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_books_api(client):
    # 1. Create Book
    book_data = {
        "title": "API Book",
        "author": "API Auth",
        "isbn": "API1",
        "total_copies": 5,
        "available_copies": 5,
    }
    response = client.post("/api/v1/books/", json=book_data)
    assert response.status_code == 201
    data = response.json()
    book_id = data["id"]
    assert data["title"] == "API Book"

    # 2. Get Book List
    response = client.get("/api/v1/books/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert len(data["data"]) > 0
    assert data["meta"]["total"] >= 1

    # 3. Get Single Book
    response = client.get(f"/api/v1/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["id"] == book_id

    # 4. Update Book
    update_data = {"title": "API Book Updated"}
    response = client.put(f"/api/v1/books/{book_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["title"] == "API Book Updated"

    # 5. Get Not Found
    response = client.get("/api/v1/books/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_members_api(client):
    import uuid

    email = f"api_{uuid.uuid4()}@e.com"
    member_data = {"name": "API Mem", "email": email}
    response = client.post("/api/v1/members/", json=member_data)
    assert response.status_code == 201
    data = response.json()
    member_id = data["id"]
    assert data["email"] == email

    # 2. Get Member List
    response = client.get("/api/v1/members/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0

    # 3. Get Single Member
    response = client.get(f"/api/v1/members/{member_id}")
    assert response.status_code == 200
    assert response.json()["member"]["id"] == member_id


def test_borrows_api(client):
    # Setup Data
    book_res = client.post(
        "/api/v1/books/",
        json={
            "title": "Bflow",
            "author": "A",
            "isbn": "BF1",
            "total_copies": 2,
            "available_copies": 2,
        },
    )
    book_id = book_res.json()["id"]
    import uuid

    member_res = client.post(
        "/api/v1/members/", json={"name": "Mflow", "email": f"mf_{uuid.uuid4()}@e.com"}
    )
    member_id = member_res.json()["id"]

    # 1. Borrow Book
    response = client.post(f"/api/v1/members/{member_id}/borrows/?book_id={book_id}")
    assert response.status_code == 201
    borrow_data = response.json()
    borrow_id = borrow_data["id"]
    assert borrow_data["status"] == "borrowed"

    # 2. List Active Borrows
    response = client.get(f"/api/v1/members/{member_id}/borrows/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == borrow_id

    # 3. List Overdue (Should be empty)
    response = client.get("/api/v1/borrows/overdue/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 0

    # 4. Return Book
    response = client.post(f"/api/v1/borrows/{borrow_id}/return/")
    assert response.status_code == 200
    assert response.json()["status"] == "returned"

    # 5. Verify Inactive
    response = client.get(f"/api/v1/members/{member_id}/borrows/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1  # It returns history now, so still 1 but returned
    assert data["data"][0]["status"] == "returned"

    # 6. Test Error Handling (Already Returned)
    response = client.post(f"/api/v1/borrows/{borrow_id}/return/")
    assert response.status_code == 409  # Conflict
    assert "already returned" in response.json()["detail"].lower()


def test_borrow_edge_cases_api(client):
    # Setup
    book_res = client.post(
        "/api/v1/books/",
        json={
            "title": "Edge",
            "author": "A",
            "isbn": "EDGE1",
            "total_copies": 1,
            "available_copies": 1,
        },
    )
    book_id = book_res.json()["id"]
    import uuid

    member_res = client.post(
        "/api/v1/members/", json={"name": "Edge Mem", "email": f"edge_{uuid.uuid4()}@e.com"}
    )
    member_id = member_res.json()["id"]

    # 1. Invalid Member w/ Valid Book
    bad_mem_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/members/{bad_mem_id}/borrows/?book_id={book_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found."

    # 2. Valid Member w/ Invalid Book
    bad_book_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/members/{member_id}/borrows/?book_id={bad_book_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found."

    # No Inventory
    # Borrow first copy
    client.post(f"/api/v1/members/{member_id}/borrows/?book_id={book_id}")
    # Borrow second copy (fail)
    response = client.post(f"/api/v1/members/{member_id}/borrows/?book_id={book_id}")
    # Same member borrowing same book again triggers ActiveBorrowExistsError (409).
    # To test InventoryUnavailableError, use a different member.

    member2_res = client.post(
        "/api/v1/members/", json={"name": "Edge Mem 2", "email": f"edge2_{uuid.uuid4()}@e.com"}
    )
    member2_id = member2_res.json()["id"]

    response = client.post(f"/api/v1/members/{member2_id}/borrows/?book_id={book_id}")
    assert response.status_code == 409
    assert "no copies available" in response.json()["detail"].lower()
