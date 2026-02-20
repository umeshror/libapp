def test_metrics_collection(client):
    # 1. Check initial state
    res = client.get("/metrics")
    assert res.status_code == 200
    initial_success = res.json()["borrow_success_count"]
    initial_failure = res.json()["borrow_failure_count"]
    initial_active = res.json()["active_borrows_gauge"]

    # 2. Perform successful borrow
    # Setup
    b_res = client.post(
        "/books/",
        json={
            "title": "Met Book",
            "author": "A",
            "isbn": "MET1",
            "total_copies": 1,
            "available_copies": 1,
        },
    )
    book_id = b_res.json()["id"]
    import uuid

    m_res = client.post(
        "/members/", json={"name": "Met Mem", "email": f"met_{uuid.uuid4()}@e.com"}
    )
    member_id = m_res.json()["id"]

    client.post(f"/members/{member_id}/borrows/?book_id={book_id}")

    # Verify increment
    res = client.get("/metrics")
    assert res.json()["borrow_success_count"] == initial_success + 1
    assert res.json()["active_borrows_gauge"] == initial_active + 1

    # 3. Perform failed borrow (No Inventory)
    # Book has 0 copies now
    import uuid

    m2_res = client.post(
        "/members/", json={"name": "Met Mem 2", "email": f"met2_{uuid.uuid4()}@e.com"}
    )
    member2_id = m2_res.json()["id"]

    client.post(f"/members/{member2_id}/borrows/?book_id={book_id}")

    # Verify failure increment
    res = client.get("/metrics")
    assert res.json()["borrow_failure_count"] == initial_failure + 1

    # 4. Return book
    borrow_res = client.get(f"/members/{member_id}/borrows/")
    borrow_id = borrow_res.json()["data"][0]["id"]
    client.post(f"/borrows/{borrow_id}/return/")

    # Verify decrement
    res = client.get("/metrics")
    assert res.json()["active_borrows_gauge"] == initial_active
