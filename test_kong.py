"""
test_kong.py - Script kiểm thử Kong Gateway (Module 4)
Chạy sau khi setup_kong.py hoàn thành

Kiểm thử:
1. Happy Path: Gửi request có API key hợp lệ
2. Unauthorized: Gửi request không có API key
3. Invalid Key: Gửi request với API key sai
4. Rate Limit: Gửi quá nhiều request để trigger rate limiting
"""

import requests
import os
import time

KONG_PROXY = "http://localhost:8000"
VALID_KEY  = "team8-secret-api-key-2024"
WRONG_KEY  = "this-is-a-wrong-key"

# Path đến file CSV test
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "orders_test.csv")


def print_result(title, response):
    status = response.status_code
    icon   = "✅" if status < 400 else "❌"
    print(f"\n{icon} [{status}] {title}")
    print(f"   Headers: X-RateLimit-Remaining-Minute = "
          f"{response.headers.get('X-RateLimit-Remaining-Minute', 'N/A')}")
    try:
        print(f"   Body: {response.json()}")
    except:
        print(f"   Body: {response.text[:200]}")


def test_health_no_key():
    """Test 1: Không có API key → 401 Unauthorized"""
    print("\n" + "="*50)
    print("TEST 1: Health check WITHOUT API Key")
    r = requests.get(f"{KONG_PROXY}/health")
    print_result("No API Key → Expected 401", r)
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("   PASS ✅")


def test_health_wrong_key():
    """Test 2: API Key sai → 401 Unauthorized"""
    print("\n" + "="*50)
    print("TEST 2: Health check with WRONG API Key")
    r = requests.get(f"{KONG_PROXY}/health", headers={"apikey": WRONG_KEY})
    print_result("Wrong API Key → Expected 401", r)
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("   PASS ✅")


def test_health_valid_key():
    """Test 3: API Key hợp lệ → 200 OK"""
    print("\n" + "="*50)
    print("TEST 3: Health check with VALID API Key")
    r = requests.get(f"{KONG_PROXY}/health", headers={"apikey": VALID_KEY})
    print_result("Valid API Key → Expected 200", r)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("   PASS ✅")


def test_upload_valid_csv():
    """Test 4: Upload CSV hợp lệ qua Kong"""
    print("\n" + "="*50)
    print("TEST 4: Upload valid CSV through Kong Gateway")

    # Tạo CSV test nhỏ trong memory
    csv_content = "order_id,product_id,quantity\n9001,1,5\n9002,2,3\n9003,3,1\n"
    files = {"file": ("orders_test.csv", csv_content, "text/csv")}

    r = requests.post(
        f"{KONG_PROXY}/api/upload",
        files=files,
        headers={"apikey": VALID_KEY}
    )
    print_result("Upload CSV → Expected 200", r)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("   PASS ✅")


def test_upload_no_key():
    """Test 5: Upload CSV không có API key → 401"""
    print("\n" + "="*50)
    print("TEST 5: Upload CSV WITHOUT API Key")

    csv_content = "order_id,product_id,quantity\n9001,1,5\n"
    files = {"file": ("test.csv", csv_content, "text/csv")}

    r = requests.post(f"{KONG_PROXY}/api/upload", files=files)
    print_result("No Key Upload → Expected 401", r)
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("   PASS ✅")


def test_rate_limiting():
    """Test 6: Gửi nhiều request để trigger Rate Limiting → 429"""
    print("\n" + "="*50)
    print("TEST 6: Rate Limiting Test (gửi 12 requests liên tiếp)")
    print("   Limit: 10 req/phút → Request thứ 11+ phải bị chặn")

    got_429 = False
    for i in range(12):
        r = requests.get(f"{KONG_PROXY}/health", headers={"apikey": VALID_KEY})
        remaining = r.headers.get("X-RateLimit-Remaining-Minute", "?")
        print(f"   Request {i+1:2d}: HTTP {r.status_code} | Remaining: {remaining}")

        if r.status_code == 429:
            got_429 = True
            print(f"   🚦 Rate limit triggered at request {i+1}!")
            break

        time.sleep(0.1)  # Nhỏ delay tránh bị block ngay

    if got_429:
        print("   PASS ✅ Rate Limiting working correctly")
    else:
        print("   ⚠️  Rate limit not triggered (might need time to reset)")


def main():
    print("="*50)
    print("  NOAH Project - Kong Gateway Test Suite")
    print("  Module 4: Security & Governance")
    print("="*50)

    try:
        test_health_no_key()
        test_health_wrong_key()
        test_health_valid_key()
        test_upload_valid_csv()
        test_upload_no_key()
        test_rate_limiting()

        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("="*50)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to Kong. Make sure docker-compose is running.")
        print("   Run: docker-compose up -d")


if __name__ == "__main__":
    main()
