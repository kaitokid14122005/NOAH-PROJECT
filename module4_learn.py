"""
╔══════════════════════════════════════════════════════════════════════╗
║          MODULE 4 — KONG GATEWAY: FILE HỌC CHI TIẾT                ║
║          CMU-CS 445 ZIS | Team 8 | NOAH Project                     ║
╚══════════════════════════════════════════════════════════════════════╝

MỤC TIÊU: Sau khi đọc file này, bạn hiểu được:
  1. Kong là gì và tại sao cần nó
  2. Cách tạo từng thành phần: Service → Route → Plugin → Consumer
  3. Luồng request đi qua Kong như thế nào
  4. Cách test để xác nhận mọi thứ hoạt động

CÁCH CHẠY:
  Bước 1: docker-compose up -d          (khởi động toàn bộ hệ thống)
  Bước 2: Chờ 30-60 giây cho Kong sẵn sàng
  Bước 3: python module4_learn.py       (file này sẽ build từng bước)
"""

import requests
import time

# ─────────────────────────────────────────────────────────────────────
# PHẦN 0: BIẾN CẤU HÌNH
# ─────────────────────────────────────────────────────────────────────

# Kong Admin API: Kong lắng nghe ở port 8001 để nhận lệnh cấu hình
# Chúng ta gọi vào đây để tạo Service, Route, Plugin, Consumer
KONG_ADMIN = "http://localhost:8001"

# Flask API đang chạy bên trong Docker network với tên "flask-api"
# Kong sẽ forward request đến địa chỉ này
# Lưu ý: Client bên ngoài KHÔNG biết địa chỉ này — chỉ Kong biết
FLASK_INTERNAL_URL = "http://flask-api:5000"

# API Keys — Mật khẩu cho từng "người dùng" của API
TEAM8_API_KEY = "team8-secret-api-key-2024"
ADMIN_API_KEY = "admin-master-key-noah"


# ─────────────────────────────────────────────────────────────────────
# PHẦN 1: CHỜ KONG SẴN SÀNG
# ─────────────────────────────────────────────────────────────────────
# Kong cần thời gian để:
#   1. Kết nối vào PostgreSQL
#   2. Đọc migration schema
#   3. Bắt đầu lắng nghe ở port 8001

def wait_for_kong(max_retries=30):
    """
    Gọi GET /status đến Kong Admin API.
    Nếu Kong trả 200 → đã sẵn sàng.
    Nếu không → chờ 3 giây và thử lại (tối đa 30 lần = 90 giây).
    """
    print("\n" + "="*60)
    print("BƯỚC 1: Kiểm tra Kong đã sẵn sàng chưa...")
    print("="*60)

    for i in range(max_retries):
        try:
            r = requests.get(f"{KONG_ADMIN}/status", timeout=3)
            if r.status_code == 200:
                print(f"✅ Kong sẵn sàng! (Thử lần {i+1})")
                return True
        except Exception:
            pass  # Kong chưa lên, tiếp tục chờ

        print(f"   ⏳ Chờ Kong... ({i+1}/{max_retries})")
        time.sleep(3)

    print("❌ Kong không phản hồi sau 90 giây. Kiểm tra docker-compose.")
    return False


# ─────────────────────────────────────────────────────────────────────
# PHẦN 2: TẠO SERVICE
# ─────────────────────────────────────────────────────────────────────
# SERVICE = Địa chỉ của server thật (Flask API) mà Kong sẽ forward đến
#
# Tại sao cần Service?
#   Kong cần biết: "Khi nhận request, tôi phải chuyển tiếp đến ĐÂU?"
#   → Service chứa thông tin đó.
#
# Không có Service → Kong không biết forward đến đâu → 404

def create_service():
    """
    Tạo một Kong Service trỏ đến Flask API.

    Kong Service ≈ như một bookmark: "Flask API nằm ở http://flask-api:5000"
    """
    print("\n" + "="*60)
    print("BƯỚC 2: Tạo Service (trỏ Kong → Flask API)")
    print("="*60)

    # PUT /services/{name} → tạo hoặc cập nhật service (idempotent)
    # Dùng PUT thay POST để tránh lỗi nếu chạy lại script
    response = requests.put(
        f"{KONG_ADMIN}/services/flask-order-service",
        json={
            "name": "flask-order-service",     # Tên service (đặt tùy ý)
            "url":  FLASK_INTERNAL_URL,         # Đây là địa chỉ Flask thật
            "connect_timeout": 60000,           # Timeout kết nối: 60 giây
            "read_timeout":    60000,           # Timeout đọc response: 60 giây
            "write_timeout":   60000,           # Timeout gửi request: 60 giây
        }
    )

    if response.status_code in [200, 201]:
        data = response.json()
        print(f"✅ Service tạo thành công!")
        print(f"   ID     : {data['id']}")
        print(f"   Tên    : {data['name']}")
        print(f"   URL    : {data['host']}:{data['port']}")
        print(f"   Ý nghĩa: Kong sẽ forward mọi request đến Flask tại địa chỉ này")
    else:
        print(f"⚠️  Lỗi tạo Service: {response.status_code} - {response.text}")


# ─────────────────────────────────────────────────────────────────────
# PHẦN 3: TẠO ROUTES
# ─────────────────────────────────────────────────────────────────────
# ROUTE = Quy tắc "URL nào → forward đến Service nào"
#
# Tại sao cần Route?
#   Service chỉ biết "forward đến Flask". Nhưng Kong cần biết:
#   "Khi client gọi /api/upload thì mới forward — còn /secret thì không"
#   → Route làm điều đó.
#
# Ví dụ thực tế:
#   Client gọi: POST http://localhost:8000/api/upload
#   Kong kiểm tra route: "/api/upload" khớp route "upload-csv-route"
#   Kong forward đến: http://flask-api:5000/api/upload

def create_routes():
    """
    Tạo 2 routes:
    1. /api/upload   (POST) → nhận file CSV đơn hàng
    2. /health       (GET)  → kiểm tra hệ thống còn sống không
    """
    print("\n" + "="*60)
    print("BƯỚC 3: Tạo Routes (định nghĩa URL nào Kong nhận)")
    print("="*60)

    routes = [
        {
            "name":    "upload-csv-route",
            "paths":   ["/api/upload"],     # URL path client gọi
            "methods": ["POST"],            # Chỉ chấp nhận POST
            # strip_path=false: giữ nguyên /api/upload khi forward Flask
            # Nếu strip_path=true: Flask chỉ nhận "/" thay vì "/api/upload"
        },
        {
            "name":    "health-check-route",
            "paths":   ["/health"],
            "methods": ["GET"],
        },
    ]

    for route in routes:
        response = requests.put(
            f"{KONG_ADMIN}/services/flask-order-service/routes/{route['name']}",
            json=route
        )

        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Route '{route['name']}' tạo thành công!")
            print(f"   Path   : {route['paths']}")
            print(f"   Method : {route['methods']}")
            print(f"   Ý nghĩa: {route['methods'][0]} http://localhost:8000{route['paths'][0]}")
        else:
            print(f"⚠️  Lỗi: {response.status_code} - {response.text}")


# ─────────────────────────────────────────────────────────────────────
# PHẦN 4: BẬT PLUGIN KEY AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────
# PLUGIN = Tính năng bổ sung cho Kong (xác thực, giới hạn, log...)
#
# Plugin key-auth hoạt động như thế nào?
#   1. Client gửi request kèm header: apikey: <key>
#   2. Kong tìm key trong danh sách consumers
#   3. Tìm thấy → request hợp lệ, cho qua
#   4. Không tìm thấy → trả 401 Unauthorized, DỪNG
#
# Tại sao cần key-auth?
#   Không có xác thực → bất kỳ ai cũng gọi được API
#   → Hacker spam, lấy/phá dữ liệu

def enable_key_auth():
    """
    Bật plugin key-auth trên toàn bộ service.
    Mọi route dưới service này đều bị kiểm tra API key.
    """
    print("\n" + "="*60)
    print("BƯỚC 4: Bật Plugin Key Authentication")
    print("="*60)

    response = requests.post(
        f"{KONG_ADMIN}/services/flask-order-service/plugins",
        json={
            "name": "key-auth",         # Tên plugin (có sẵn trong Kong)
            "config": {
                "key_names": ["apikey"],    # Tên header client phải gửi
                                            # Client gửi: apikey: <key>
                "hide_credentials": True,   # Xóa header apikey trước khi
                                            # forward đến Flask
                                            # → Flask không thấy API key
                                            # → Bảo mật hơn
                "key_in_header": True,      # Cho phép gửi key qua header
                "key_in_query":  False,     # KHÔNG cho phép gửi key qua
                                            # query string (?apikey=xxx)
                                            # → An toàn hơn
            }
        }
    )

    if response.status_code in [200, 201]:
        print("✅ Plugin Key Auth đã bật!")
        print("   Từ bây giờ: mọi request PHẢI có header 'apikey: <key>'")
        print("   Thiếu/sai key → Kong trả HTTP 401 Unauthorized")
        print("   Đúng key     → Kong tiếp tục xử lý")
    else:
        print(f"⚠️  Lỗi: {response.status_code} - {response.text}")


# ─────────────────────────────────────────────────────────────────────
# PHẦN 5: BẬT PLUGIN RATE LIMITING
# ─────────────────────────────────────────────────────────────────────
# Plugin rate-limiting đếm số request của mỗi consumer trong khoảng thời gian
# Nếu vượt ngưỡng → trả 429 Too Many Requests
#
# Tại sao cần rate limiting?
#   Một consumer có thể gửi 10,000 request/giây → server crash
#   → Rate limiting bảo vệ Flask API khỏi bị quá tải
#
# Header Kong trả về để client biết còn bao nhiêu request:
#   X-RateLimit-Remaining-Minute: 7   ← còn 7 request trong phút này
#   X-RateLimit-Remaining-Hour: 95    ← còn 95 request trong giờ này

def enable_rate_limiting():
    """
    Giới hạn: mỗi consumer tối đa 10 request/phút, 100 request/giờ.
    """
    print("\n" + "="*60)
    print("BƯỚC 5: Bật Plugin Rate Limiting")
    print("="*60)

    response = requests.post(
        f"{KONG_ADMIN}/services/flask-order-service/plugins",
        json={
            "name": "rate-limiting",
            "config": {
                "minute": 10,               # Tối đa 10 request / phút
                "hour":   100,              # Tối đa 100 request / giờ
                                            # Request thứ 11 trong phút
                                            # → Kong trả 429, không forward Flask

                "policy": "local",          # Đếm trong RAM của Kong
                                            # "redis" → dùng Redis (distributed)
                                            # "local" → đủ dùng cho demo

                "fault_tolerant":    True,  # Nếu plugin lỗi → vẫn cho request qua
                                            # False → plugin lỗi → chặn hết
                "hide_client_headers": False, # Gửi header X-RateLimit-* về client
                                              # True → ẩn, client không biết limit
            }
        }
    )

    if response.status_code in [200, 201]:
        print("✅ Plugin Rate Limiting đã bật!")
        print("   Giới hạn: 10 request/phút, 100 request/giờ mỗi consumer")
        print("   Vượt ngưỡng → Kong trả HTTP 429 Too Many Requests")
        print("   Header X-RateLimit-Remaining-Minute sẽ đếm ngược")
    else:
        print(f"⚠️  Lỗi: {response.status_code} - {response.text}")


# ─────────────────────────────────────────────────────────────────────
# PHẦN 6: TẠO CONSUMERS VÀ API KEYS
# ─────────────────────────────────────────────────────────────────────
# CONSUMER = "Người dùng" đã được đăng ký trong Kong
#
# Cách hoạt động:
#   Kong nhận request có header: apikey: team8-secret-api-key-2024
#   Kong tra cứu: key này thuộc consumer nào?
#   → Tìm thấy "team8-client" → Cho phép
#   → Không tìm thấy → 401 Unauthorized
#
# Mỗi consumer có thể có nhiều API key khác nhau.
# Rate limiting áp dụng riêng cho từng consumer.

def create_consumers():
    """
    Tạo 2 consumers:
    - team8-client: Consumer chính của nhóm 8
    - admin-user:   Consumer admin với quyền cao hơn (demo)
    """
    print("\n" + "="*60)
    print("BƯỚC 6: Tạo Consumers và API Keys")
    print("="*60)

    consumers = [
        {
            "username": "team8-client",
            "key":      TEAM8_API_KEY,
            "note":     "Consumer chính của nhóm 8 — dùng cho demo và test"
        },
        {
            "username": "admin-user",
            "key":      ADMIN_API_KEY,
            "note":     "Consumer admin — dùng cho quản trị viên"
        },
    ]

    for c in consumers:
        # Bước 6a: Tạo consumer (đăng ký "người dùng")
        r1 = requests.put(
            f"{KONG_ADMIN}/consumers/{c['username']}",
            json={"username": c["username"]}
        )

        if r1.status_code in [200, 201]:
            print(f"\n✅ Consumer '{c['username']}' đã tạo!")
            print(f"   Ghi chú: {c['note']}")

        # Bước 6b: Tạo API Key cho consumer đó
        # Consumer chưa có key → không dùng được gì
        # Consumer + key → có thể gọi API
        r2 = requests.post(
            f"{KONG_ADMIN}/consumers/{c['username']}/key-auth",
            json={"key": c["key"]}
        )

        if r2.status_code in [200, 201]:
            print(f"   🔑 API Key: {c['key']}")
            print(f"   Dùng: curl -H 'apikey: {c['key']}' http://localhost:8000/health")
        else:
            # Key đã tồn tại (chạy lại script) — không phải lỗi nghiêm trọng
            print(f"   ℹ️  Key đã tồn tại (có thể đã setup trước đó)")


# ─────────────────────────────────────────────────────────────────────
# PHẦN 7: XÁC NHẬN CẤU HÌNH
# ─────────────────────────────────────────────────────────────────────

def verify_setup():
    """
    Gọi Admin API để in ra toàn bộ cấu hình hiện tại.
    Dùng để xác nhận mọi thứ đã được tạo đúng.
    """
    print("\n" + "="*60)
    print("BƯỚC 7: Xác nhận toàn bộ cấu hình")
    print("="*60)

    # Liệt kê Services
    services = requests.get(f"{KONG_ADMIN}/services").json().get("data", [])
    print(f"\n📦 Services ({len(services)}):")
    for s in services:
        print(f"   [{s['name']}] → {s['host']}:{s['port']}")

    # Liệt kê Routes
    routes = requests.get(f"{KONG_ADMIN}/routes").json().get("data", [])
    print(f"\n🛣️  Routes ({len(routes)}):")
    for r in routes:
        print(f"   [{r['name']}] {r['methods']} {r['paths']}")

    # Liệt kê Plugins
    plugins = requests.get(f"{KONG_ADMIN}/plugins").json().get("data", [])
    print(f"\n🔌 Plugins ({len(plugins)}):")
    for p in plugins:
        print(f"   [{p['name']}]")

    # Liệt kê Consumers
    consumers = requests.get(f"{KONG_ADMIN}/consumers").json().get("data", [])
    print(f"\n👤 Consumers ({len(consumers)}):")
    for c in consumers:
        print(f"   [{c['username']}]")


# ─────────────────────────────────────────────────────────────────────
# PHẦN 8: DEMO — GỬI REQUEST QUA KONG
# ─────────────────────────────────────────────────────────────────────

def demo_requests():
    """
    Gửi thử các request để thấy Kong hoạt động thực tế.
    """
    print("\n" + "="*60)
    print("BƯỚC 8: Demo — Gửi request thực tế qua Kong")
    print("="*60)

    KONG_PROXY = "http://localhost:8000"

    # Demo 1: Không có API key → 401
    print("\n[Demo 1] Gọi /health KHÔNG có apikey:")
    r = requests.get(f"{KONG_PROXY}/health")
    print(f"  HTTP {r.status_code} → {'❌ CHẶN (đúng!)' if r.status_code == 401 else r.text}")

    # Demo 2: API key sai → 401
    print("\n[Demo 2] Gọi /health với apikey SAI:")
    r = requests.get(f"{KONG_PROXY}/health", headers={"apikey": "wrong-key"})
    print(f"  HTTP {r.status_code} → {'❌ CHẶN (đúng!)' if r.status_code == 401 else r.text}")

    # Demo 3: API key đúng → 200
    print("\n[Demo 3] Gọi /health với apikey ĐÚNG:")
    r = requests.get(f"{KONG_PROXY}/health", headers={"apikey": TEAM8_API_KEY})
    remaining = r.headers.get("X-RateLimit-Remaining-Minute", "?")
    print(f"  HTTP {r.status_code} → {'✅ ĐƯỢC PHÉP' if r.status_code == 200 else r.text}")
    print(f"  Còn lại trong phút: {remaining} request")

    # Demo 4: Rate limiting
    print("\n[Demo 4] Gọi /health 12 lần liên tiếp (limit=10/phút):")
    for i in range(12):
        r = requests.get(f"{KONG_PROXY}/health", headers={"apikey": TEAM8_API_KEY})
        remaining = r.headers.get("X-RateLimit-Remaining-Minute", "?")
        status_icon = "✅" if r.status_code == 200 else "🚫 RATE LIMITED"
        print(f"  Request {i+1:2d}: HTTP {r.status_code} {status_icon} | Còn: {remaining}")
        if r.status_code == 429:
            print("  → Kong trả 429 Too Many Requests ✅ Rate Limiting hoạt động!")
            break


# ─────────────────────────────────────────────────────────────────────
# MAIN: Chạy tuần tự từng bước
# ─────────────────────────────────────────────────────────────────────

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     MODULE 4 — KONG GATEWAY SETUP (Phiên bản học tập)  ║
║     Mỗi bước sẽ được giải thích rõ ràng                ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Bước 1: Chờ Kong sẵn sàng
    if not wait_for_kong():
        print("\n💡 Gợi ý: Chạy 'docker-compose up -d' trước, chờ 60s rồi thử lại")
        return

    # Bước 2-6: Xây dựng từng thành phần
    create_service()      # SERVICE: địa chỉ Flask
    create_routes()       # ROUTE: URL nào được phép
    enable_key_auth()     # PLUGIN: xác thực API key
    enable_rate_limiting()# PLUGIN: giới hạn tốc độ
    create_consumers()    # CONSUMER: đăng ký người dùng + key

    # Bước 7: Xác nhận
    verify_setup()

    # Bước 8: Demo
    print("\n" + "="*60)
    run_demo = input("Chạy demo request thực tế? (y/n): ").strip().lower()
    if run_demo == "y":
        demo_requests()

    # Tổng kết
    print("""
╔══════════════════════════════════════════════════════════╗
║                  TỔNG KẾT MODULE 4                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  SERVICE     → Kong biết Flask ở đâu                    ║
║  ROUTE       → Kong biết URL nào được phép              ║
║  key-auth    → Kiểm tra API key (401 nếu sai)           ║
║  rate-limit  → Giới hạn 10 req/phút (429 nếu vượt)     ║
║  CONSUMER    → Người dùng đã đăng ký với key riêng      ║
║                                                          ║
║  Endpoint chính:                                         ║
║  POST http://localhost:8000/api/upload                   ║
║  Header: apikey: team8-secret-api-key-2024               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
