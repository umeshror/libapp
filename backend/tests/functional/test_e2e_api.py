def test_full_borrow_flow(client):
    # 1. Create Book
    # Total Copies = 2, Available = 2
    book_payload = {
        "title": "E2E Lifecycle Book",
        "author": "E2E Author",
        "isbn": "E2E-999",
        "total_copies": 2,
        "available_copies": 2,
    }
    book_res = client.post("/books/", json=book_payload)
    assert book_res.status_code == 201
    book_data = book_res.json()
    book_id = book_data["id"]

    # 2. Create Member
    member_payload = {"name": "E2E Lifecycle Member", "email": "e2e_cycle@example.com"}
    mem_res = client.post("/members/", json=member_payload)
    assert mem_res.status_code == 201
    member_data = mem_res.json()
    member_id = member_data["id"]

    # Invariant Check (Initial)
    # Active borrows (0) <= Total (2)
    borrows_res = client.get(f"/members/{member_id}/borrows/")
    borrows_data = borrows_res.json()["data"]
    assert len(borrows_data) == 0

    # 3. Borrow Book
    # Expected: 201 Created
    # Use standard POST /borrows/ rather than deprecated endpoint
    borrow_payload = {"book_id": str(book_id), "member_id": str(member_id)}
    borrow_res = client.post(f"/borrows/", json=borrow_payload)
    assert borrow_res.status_code == 201
    borrow_data = borrow_res.json()
    borrow_id = borrow_data["id"]

    # 4. Validate Invariants after Borrow
    # Inventory should be 1
    book_check = client.get(f"/books/{book_id}")
    assert book_check.json()["available_copies"] == 1
    assert book_check.json()["available_copies"] >= 0  # "Inventory never negative"

    # Active Borrows should be 1
    borrows_res = client.get(f"/members/{member_id}/borrows/")
    borrows_data = borrows_res.json()["data"]
    # Filter for active borrows
    active_borrows = [b for b in borrows_data if b["status"] == "borrowed"]
    assert len(active_borrows) == 1

    # Active borrows (1) <= Total (2)
    assert len(active_borrows) <= book_check.json()["total_copies"]

    # 5. Return Book
    return_res = client.post(f"/borrows/{borrow_id}/return/")
    assert return_res.status_code == 200
    assert return_res.json()["status"] == "returned"

    # 6. Validate Resotration & Invariants
    # Inventory should be restored to 2
    book_check = client.get(f"/books/{book_id}")
    assert book_check.json()["available_copies"] == 2

    # Active Borrows should be 0
    borrows_res = client.get(f"/members/{member_id}/borrows/")
    borrows_data = borrows_res.json()["data"]
    active_borrows = [b for b in borrows_data if b["status"] == "borrowed"]
    assert len(active_borrows) == 0

    # Final Invariant Check
    # Active borrows (0) <= Total (2)
    assert 0 <= book_check.json()["total_copies"]
