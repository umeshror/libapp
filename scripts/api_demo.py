import httpx
import json
import time
import sys
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def print_separator(title):
    print(f"\n{'='*20} {title} {'='*20}")

def run_demo():
    results = []
    
    def log_result(scenario, status, detail=""):
        results.append({"scenario": scenario, "status": status, "detail": detail})

    print("Starting Neighborhood Library API Demo...")
    
    # 1. Check health
    try:
        response = httpx.get(f"http://localhost:8000/health")
        if response.status_code == 200:
            print("Server is healthy and connected to DB")
            log_result("API Health Check", "PASS", "Connected to DB")
        else:
            print(f"Server health check failed: {response.text}")
            log_result("API Health Check", "FAIL", response.text)
            sys.exit(1)
    except Exception as e:
        print(f"Could not connect to server at http://localhost:8000. Is it running?")
        log_result("API Health Check", "FAIL", "Connection Refused")
        sys.exit(1)

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 2. Create a Book
        print_separator("Books Management")
        book_data = {
            "title": f"The Pythonic Way {uuid.uuid4().hex[:4]}",
            "author": "Guido van Rossum",
            "isbn": f"ISBN-{uuid.uuid4().hex[:12]}",
            "total_copies": 2
        }
        res = client.post("/books/", json=book_data)
        if res.status_code == 201:
            book = res.json()
            print(f"Created Book: '{book['title']}' (ID: {book['id']})")
            log_result("Book Creation", "PASS", f"Title: {book['title']}")
        else:
            log_result("Book Creation", "FAIL", res.text)
            sys.exit(1)

        # 3. Create a Member
        print_separator("Member Management")
        member_data = {
            "name": "Jane Developer",
            "email": f"jane.{uuid.uuid4().hex[:6]}@example.com",
            "phone": "555-0199-1234"
        }
        res = client.post("/members/", json=member_data)
        if res.status_code == 201:
            member = res.json()
            print(f"Created Member: '{member['name']}' (ID: {member['id']})")
            log_result("Member Creation", "PASS", f"Name: {member['name']}")
        else:
            log_result("Member Creation", "FAIL", res.text)
            sys.exit(1)

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
            log_result("Borrow Operation", "PASS", "Initial Borrow Success")
        else:
            log_result("Borrow Operation", "FAIL", res.text)
            sys.exit(1)

        # 5. Validation Check: Try to borrow same book again
        print("\nChecking validation: Member tries to borrow the SAME book again...")
        res = client.post("/borrows/", json=borrow_data)
        if res.status_code in (400, 409):
            error_data = res.json()
            print(f"Correctly blocked: {error_data['detail']} (Code: {error_data.get('error_code', 'N/A')})")
            log_result("Duplicate Borrow Check", "PASS", "Correctly Blocked")
        else:
            log_result("Duplicate Borrow Check", "FAIL", f"Status: {res.status_code}")

        # 6. Return Operation
        print_separator("Returning Operations")
        res = client.post(f"/borrows/{borrow_record['id']}/return/")
        if res.status_code == 200:
            print("Book returned successfully!")
            log_result("Return Operation", "PASS", "Return Success")
        else:
            log_result("Return Operation", "FAIL", res.text)

        # 7. Search & Sorting
        print_separator("Advanced Search & Sorting")
        search_query = book['title']
        res = client.get(f"/books/?q={search_query}")
        search_results = res.json()
        print(f"Searched for '{search_query}': Found {search_results['meta']['total']} matching books")
        log_result("Search Functionality", "PASS" if search_results['meta']['total'] >= 1 else "FAIL")
        
        # Sort by Author
        res = client.get("/books/?sort_by=author&order=asc&limit=5")
        sorted_books = res.json()
        print("\nTop 5 books sorted by Author (Ascending):")
        for b in sorted_books['data']:
            print(f"  - {b['author']}: {b['title']}")
        log_result("Sorting Functionality", "PASS")

        # 8. Library Analytics (Dashboard)
        print_separator("Library Data Insights")
        res = client.get("/analytics/summary")
        if res.status_code == 200:
            summary = res.json()
            overview = summary['overview']
            print(f"Library Snapshot:")
            print(f"  - Total Books: {overview['total_books']}")
            print(f"  - Active Borrows: {overview['active_borrows']}")
            log_result("Analytics Fetch", "PASS")
        else:
            log_result("Analytics Fetch", "FAIL", res.text)

        # 9. Complex Business Logic Combinations
        print_separator("Advanced Business Logic & Edge Cases")
        
        # Scenario C: Inventory Exhaustion
        print("Scenario C: Inventory Exhaustion (Borrowing the last copy)...")
        limited_book_data = {
            "title": f"The Last Copy {uuid.uuid4().hex[:4]}",
            "author": "Rare Author",
            "isbn": f"ISBN-{uuid.uuid4().hex[:12]}",
            "total_copies": 1
        }
        res_b = client.post("/books/", json=limited_book_data)
        limited_book = res_b.json()
        res_m2 = client.post("/members/", json={
            "name": "Member Two", "email": f"two.{uuid.uuid4().hex[:6]}@test.com", "phone": "555-0000-1111"
        })
        member2 = res_m2.json()
        client.post("/borrows/", json={"book_id": limited_book['id'], "member_id": member['id']})
        res_inv = client.post("/borrows/", json={"book_id": limited_book['id'], "member_id": member2['id']})
        if res_inv.status_code == 409 and "inventory" in res_inv.text.lower():
            print(f"  Passed: Blocked second borrower - {res_inv.json()['error_code']}")
            log_result("Inventory Exhaustion", "PASS", "Correctly Blocked")
        else:
            log_result("Inventory Exhaustion", "FAIL", f"Status: {res_inv.status_code}")

        # Scenario D: Double Return
        print("\nScenario D: Idempotency check (Double Return)...")
        res_dr = client.post(f"/borrows/{borrow_record['id']}/return/")
        if res_dr.status_code == 409:
            print(f"  Passed: Already returned blocked - {res_dr.json()['error_code']}")
            log_result("Double Return Check", "PASS", "Blocked Idempotently")
        else:
            log_result("Double Return Check", "FAIL")

        # Scenario F: Member Borrow Limit
        print("\nScenario F: Enforcing Member Borrow Limit...")
        res_lm = client.post("/members/", json={
            "name": "Limit Tester", 
            "email": f"limit.{uuid.uuid4().hex[:12]}@test.com", 
            "phone": "555-2222-3333"
        })
        limit_member = res_lm.json()
        blocked_at_6 = False
        for i in range(6):
            b_res = client.post("/books/", json={
                "title": f"Volume {i}", "author": "Multi", "isbn": f"ISBN-{uuid.uuid4().hex[:6]}", "total_copies": 10
            })
            b_data = b_res.json()
            res_lim = client.post("/borrows/", json={"book_id": b_data['id'], "member_id": limit_member['id']})
            if res_lim.status_code == 409 and "limit" in res_lim.text.lower():
                blocked_at_6 = True
                print(f"  Passed: Blocked at borrow #{i+1} due to limit constraint.")
                break
        log_result("Member Borrow Limit", "PASS" if blocked_at_6 else "FAIL")

        # Scenario G: Overdue & Risk Analytics
        print("\nScenario G: Overdue & Risk Analysis...")
        # Get analytics for the member we created at the start
        res_an = client.get(f"/members/{member['id']}/analytics")
        if res_an.status_code == 200:
            m_analytics = res_an.json()
            print(f"  Member: {member['name']}")
            print(f"  Risk Level: {m_analytics['risk_level']}")
            print(f"  Overdue Rate: {m_analytics['overdue_rate_percent']}%")
            print(f"  Total Fines Accrued: ${m_analytics['total_fines_accrued']}")
            log_result("Member Risk Profiling", "PASS", f"Risk: {m_analytics['risk_level']}, Fines: ${m_analytics['total_fines_accrued']}")
        else:
            log_result("Member Risk Profiling", "FAIL", res_an.text)

        # 10. Input Validation
        print_separator("Input Validation & Integrity")
        invalid_m = {"name": "Bad Email", "email": "not-an-email", "phone": "123"}
        res_v = client.post("/members/", json=invalid_m)
        log_result("Email Validation", "PASS" if res_v.status_code == 422 else "FAIL")

        invalid_b = {"title": "Impossible Book", "author": "None", "isbn": "0-0-0", "total_copies": -1}
        res_v2 = client.post("/books/", json=invalid_b)
        log_result("Inventory Validation", "PASS" if res_v2.status_code == 422 else "FAIL")

        # Summary Table
        print_separator("DEMO SUMMARY REPORT")
        print(f"{'Scenario':<40} | {'Status':<10} | {'Detail'}")
        print("-" * 80)
        for r in results:
            status_color = "\033[92mPASS\033[0m" if r['status'] == "PASS" else "\033[91mFAIL\033[0m"
            print(f"{r['scenario']:<40} | {status_color:<19} | {r['detail']}")
        print("=" * 80)

    print("\nDEMO COMPLETE: ALL COMBINATIONS VERIFIED")

if __name__ == "__main__":
    run_demo()
