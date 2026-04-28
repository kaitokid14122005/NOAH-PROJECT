"""
setup_kong.py - Script tự động cấu hình Kong Gateway qua Admin API
Module 4: Security & Governance

Chạy sau khi docker-compose up:
    python setup_kong.py
"""

import requests
import time

KONG_ADMIN = "http://localhost:8001"
FLASK_URL  = "http://flask-api:5000"   # Tên trong docker network


def wait_for_kong():
    """Chờ Kong sẵn sàng"""
    print("[Setup] Waiting for Kong Admin API...")
    for i in range(30):
        try:
            r = requests.get(f"{KONG_ADMIN}/status", timeout=3)
            if r.status_code == 200:
                print("[Setup] ✅ Kong is ready!")
                return True
        except:
            pass
        print(f"[Setup] Attempt {i+1}/30... retrying in 3s")
        time.sleep(3)
    return False


def create_service():
    """Tạo Service: trỏ Kong → Flask API"""
    print("\n[Setup] Creating Service (Flask API)...")
    payload = {
        "name": "flask-order-service",
        "url":  FLASK_URL,
        "connect_timeout": 60000,
        "read_timeout":    60000,
        "write_timeout":   60000,
    }
    r = requests.put(f"{KONG_ADMIN}/services/flask-order-service", json=payload)
    if r.status_code in [200, 201]:
        print(f"[Setup] ✅ Service created: {r.json()['id']}")
    else:
        print(f"[Setup] ⚠️  Service response: {r.status_code} - {r.text}")


def create_routes():
    """Tạo Routes: định nghĩa URL path Kong expose"""
    routes = [
        {
            "name":    "upload-csv-route",
            "paths":   ["/api/upload"],
            "methods": ["POST"],
        },
        {
            "name":    "health-check-route",
            "paths":   ["/health"],
            "methods": ["GET"],
        },
    ]

    print("\n[Setup] Creating Routes...")
    for route in routes:
        r = requests.put(
            f"{KONG_ADMIN}/services/flask-order-service/routes/{route['name']}",
            json=route
        )
        if r.status_code in [200, 201]:
            print(f"[Setup] ✅ Route created: {route['name']}")
        else:
            print(f"[Setup] ⚠️  Route response: {r.status_code} - {r.text}")


def enable_key_auth():
    """Enable Key Authentication plugin trên Service"""
    print("\n[Setup] Enabling Key Authentication plugin...")
    payload = {
        "name": "key-auth",
        "config": {
            "key_names":        ["apikey"],
            "hide_credentials": True,
            "key_in_header":    True,
            "key_in_query":     False,
        }
    }
    r = requests.post(
        f"{KONG_ADMIN}/services/flask-order-service/plugins",
        json=payload
    )
    if r.status_code in [200, 201]:
        print(f"[Setup] ✅ Key Auth enabled!")
    else:
        print(f"[Setup] ⚠️  Key Auth response: {r.status_code} - {r.text}")


def enable_rate_limiting():
    """Enable Rate Limiting plugin trên Service"""
    print("\n[Setup] Enabling Rate Limiting plugin...")
    payload = {
        "name": "rate-limiting",
        "config": {
            "minute":           10,     # Tối đa 10 req/phút
            "hour":             100,    # Tối đa 100 req/giờ
            "policy":           "local",
            "fault_tolerant":   True,
            "hide_client_headers": False,
        }
    }
    r = requests.post(
        f"{KONG_ADMIN}/services/flask-order-service/plugins",
        json=payload
    )
    if r.status_code in [200, 201]:
        print(f"[Setup] ✅ Rate Limiting enabled!")
    else:
        print(f"[Setup] ⚠️  Rate Limiting response: {r.status_code} - {r.text}")


def create_consumers():
    """Tạo Consumer và API Keys"""
    consumers = [
        {"username": "team8-client",  "key": "team8-secret-api-key-2024"},
        {"username": "admin-user",    "key": "admin-master-key-noah"},
    ]

    print("\n[Setup] Creating Consumers and API Keys...")
    for consumer in consumers:
        # Tạo consumer
        r = requests.put(
            f"{KONG_ADMIN}/consumers/{consumer['username']}",
            json={"username": consumer["username"]}
        )
        if r.status_code in [200, 201]:
            print(f"[Setup] ✅ Consumer created: {consumer['username']}")

        # Tạo API key cho consumer
        r2 = requests.post(
            f"{KONG_ADMIN}/consumers/{consumer['username']}/key-auth",
            json={"key": consumer["key"]}
        )
        if r2.status_code in [200, 201]:
            print(f"[Setup] ✅ API Key assigned: {consumer['key']}")
        else:
            print(f"[Setup] ⚠️  Key response: {r2.status_code} - {r2.text}")


def verify_setup():
    """Kiểm tra cấu hình Kong"""
    print("\n" + "="*50)
    print("[Setup] VERIFICATION")
    print("="*50)

    # List services
    r = requests.get(f"{KONG_ADMIN}/services")
    services = r.json().get("data", [])
    print(f"\n📦 Services ({len(services)}):")
    for s in services:
        print(f"   - {s['name']} → {s['host']}:{s['port']}")

    # List routes
    r = requests.get(f"{KONG_ADMIN}/routes")
    routes = r.json().get("data", [])
    print(f"\n🛣️  Routes ({len(routes)}):")
    for rt in routes:
        print(f"   - {rt['name']}: {rt['paths']} [{rt['methods']}]")

    # List plugins
    r = requests.get(f"{KONG_ADMIN}/plugins")
    plugins = r.json().get("data", [])
    print(f"\n🔌 Plugins ({len(plugins)}):")
    for p in plugins:
        print(f"   - {p['name']}")

    # List consumers
    r = requests.get(f"{KONG_ADMIN}/consumers")
    consumers = r.json().get("data", [])
    print(f"\n👤 Consumers ({len(consumers)}):")
    for c in consumers:
        print(f"   - {c['username']}")


def main():
    print("="*50)
    print("  NOAH Project - Kong Gateway Setup")
    print("  Module 4: Security & Governance")
    print("="*50)

    if not wait_for_kong():
        print("[Setup] ❌ Kong is not reachable. Make sure docker-compose is running.")
        return

    create_service()
    create_routes()
    enable_key_auth()
    enable_rate_limiting()
    create_consumers()
    verify_setup()

    print("\n" + "="*50)
    print("✅ Kong setup completed!")
    print("\nAPI Endpoints (qua Kong Gateway):")
    print("  POST http://localhost:8000/api/upload")
    print("       Header: apikey: team8-secret-api-key-2024")
    print("  GET  http://localhost:8000/health")
    print("       Header: apikey: team8-secret-api-key-2024")
    print("="*50)


if __name__ == "__main__":
    main()
