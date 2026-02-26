import httpx
import json
import time
import sys
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def print_separator(title):
    print(f"\n{'='*20} {title} {'='*20}")

def run_demo():
    print("Starting Neighborhood Library API Demo...")
    
    # 1. Check health
    try:
        response = httpx.get(f"http://localhost:8000/health")
        if response.status_code == 200:
            print("Server is healthy and connected to DB")
        else:
            print(f"Server health check failed: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Could not connect to server at http://localhost:8000. Is it running?")
        print("Run 'make start' in another terminal first.")
        sys.exit(1)

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 2. Create a Book
        print_separator("Books Management")
        book_data = {
            "title": f"The Pythonic Way {uuid.uuid4().hex[:4]}",
            "author": "Guido van Rossum",
            "isbn": f"978-{str(time.time()).replace('.', '')[:10]}",
            "total_copies": 2
        }
        res = client.post("/books/", json=book_data)
        book = res.json()
        print(f"Created Book: '{book['title']}' (ID: {book['id']})")

        # 3. Create a Member
        print_separator("Member Management")
        member_data = {
            "name": "Jane Developer",
            "email": f"jane.{uuid.uuid4().hex[:6]}@example.com",
            "phone": "555-0199-1234"
        }
        res = client.post("/members/", json=member_data)
        member = res.json()
        print(f"Created Member: '{member['name']}' (ID: {member['id']})")

        # 4. Borrow Operation
        print_separator("Borrowing Operations")
        borrow_data = {
            "book_id": book["id"],
            "member_id": member["id"]
        }
        res = client.post("/borrows/", json=borrow_data)
        if res.status_code in (200, 201):
            borrow_record = res.json()
            print(f"Borrow recorded! Due date: {borrow_record['due_date']}")
        else:
            print(f"Failed to borrow: {res.text}")
            sys.exit(1)

        # 5. Validation Check: Try to borrow same book again
        print("\nChecking validation: Member tries to borrow the SAME book again...")
        res = client.post("/borrows/", json=borrow_data)
        if res.status_code in (400, 409):
            error_data = res.json()
            print(f"Correctly blocked: {error_data['detail']} (Code: {error_data.get('error_code', 'N/A')})")
        else:
            print(f"Unexpected result for duplicate borrow: {res.status_code}")

        # 6. Return Operation
        print_separator("Returning Operations")
        res = client.post(f"/borrows/{borrow_record['id']}/return/")
        if res.status_code == 200:
            print("Book returned successfully!")
        else:
            print(f"Return failed: {res.text}")

        # 7. List Member's History
        print_separator("Querying History")
        res = client.get(f"/members/{member['id']}/borrows/")
        history = res.json()
        print(f"Found {history['meta']['total']} records for {member['name']}")
        for item in history['data']:
            print(f"  - {item['book']['title']} | Status: {item['status']} | Borrowed: {item['borrowed_at']}")

    print_separator("DEMO COMPLETE")

if __name__ == "__main__":
    run_demo()
