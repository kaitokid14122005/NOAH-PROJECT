# NOAH Project — Kiến trúc & Giải thích toàn bộ hệ thống

## 1. Tổng quan kiến trúc

```
[inventory.csv] → [cleaner.py] → [clean_inventory.csv]   ← MODULE 1

[Client HTTP]
     ↓
[Kong Gateway :8000]  ← kiểm tra API key, giới hạn tốc độ  ← MODULE 4
     ↓
[Flask API :5000]     ← nhận CSV, đẩy vào queue
     ↓
[RabbitMQ :5672]      ← hàng đợi message
     ↓
[Worker]              ← đọc queue, INSERT vào MySQL         ← MODULE 2
     ↓
[MySQL :3306]         ← lưu trữ orders, products
```

---

## 2. DOCKER — Tại sao dùng và hoạt động ra sao

### Docker là gì?
Docker đóng gói một ứng dụng cùng toàn bộ dependencies của nó vào một "container" — chạy giống nhau trên mọi máy tính.

### docker-compose.yml — Khởi động 7 container cùng lúc

| Container | Image | Chức năng |
|---|---|---|
| `noah-mysql` | mysql:8.0 | Database business (sản phẩm, đơn hàng) |
| `noah-rabbitmq` | rabbitmq:3-management | Message queue |
| `noah-flask-api` | Build từ Dockerfile.api | Web server nhận CSV |
| `noah-worker` | Build từ Dockerfile.worker | Xử lý queue, ghi DB |
| `noah-kong-db` | postgres:13 | Database riêng của Kong |
| `noah-kong-migration` | kong:3.4 | Tạo bảng trong PostgreSQL (chạy 1 lần) |
| `noah-kong` | kong:3.4 | API Gateway bảo vệ Flask |

### Docker Network
Tất cả container cùng trong `noah-network` — giao tiếp qua tên container:
- Flask gọi RabbitMQ: `host = "rabbitmq"` (không phải localhost)
- Worker gọi MySQL: `host = "mysql"`
- Kong forward Flask: `url = "http://flask-api:5000"`

### Port mapping (ra ngoài host)
```
localhost:8000 → Kong Proxy     (Client gửi request vào đây)
localhost:8001 → Kong Admin     (setup_kong.py cấu hình qua đây)
localhost:5000 → Flask          (debug trực tiếp, bypass Kong)
localhost:15672 → RabbitMQ UI   (xem queue trên trình duyệt)
localhost:3306 → MySQL          (kết nối bằng Workbench)
```

---

## 3. HAI DATABASE — Hai mục đích khác nhau

### MySQL (`noah_db`) — Dữ liệu business

**Khởi tạo:** Khi MySQL container start, nó tự đọc `data/init.sql` và tạo bảng + seed data.

```sql
-- Bảng sản phẩm (seed sẵn 200 sản phẩm id 100-299)
products (id PK, name, price, stock INT DEFAULT 0)

-- Bảng đơn hàng (seed sẵn 20,000 đơn mẫu)
orders (id PK AUTO_INCREMENT, user_id, product_id FK, quantity, total_price, status, created_at)
```

**Ai dùng:** Worker đọc/ghi, Flask API đọc (kiểm tra product tồn tại).

### PostgreSQL (`kong`) — Cấu hình Kong

**Khởi tạo:** `kong-migration` container chạy `kong migrations bootstrap` → tạo schema.

**Chứa gì:** Kong tự quản lý. Nó lưu Services, Routes, Plugins, Consumers, API Keys.

**Ai dùng:** Chỉ Kong Gateway. Bạn không cần viết SQL vào đây — `setup_kong.py` quản lý qua REST API.

---

## 4. MODULE 1 — Làm sạch dữ liệu

### Vấn đề: `data/inventory.csv` có dữ liệu bẩn

```
product_id,quantity      ← header
274,204                  ← OK
243,459,ExtraData        ← LỖI: EXTRA_COLUMNS (cột dư)
101,53,ExtraData         ← LỖI: EXTRA_COLUMNS
-1,100                   ← LỖI: product_id âm
abc,50                   ← LỖI: không phải số
```

### Cách xử lý trong `src/cleaner.py`

```python
parts = line.split(",")

if len(parts) > 2:          # EXTRA_COLUMNS → cắt bỏ cột dư
    parts = parts[:2]

if len(parts) < 2:          # Thiếu cột → bỏ qua dòng
    skip()

product_id = int(parts[0])  # Không phải số → bỏ qua (try-except)
quantity   = int(parts[1])

if quantity < 0:             # Âm → bỏ qua
    skip()

if product_id in data:       # Trùng → cộng dồn quantity
    data[product_id] += quantity
else:
    data[product_id] = quantity
```

### Kết quả

```
Input:  data/inventory.csv      (5001 dòng, có lỗi)
Output: output/clean_inventory.csv  (201 sản phẩm, sạch)
Log:    logs/error.log          (ghi lại mọi lỗi)
```

---

## 5. MODULE 2 — Xử lý đơn hàng bất đồng bộ

### Tại sao dùng RabbitMQ thay vì INSERT trực tiếp?

**Không dùng queue (vấn đề):**
Client upload 10,000 đơn → Flask phải INSERT 10,000 dòng → mất 30 giây → Client timeout.

**Dùng queue (giải pháp):**
- Flask nhận CSV → đẩy 10,000 message vào queue (< 1 giây) → trả kết quả ngay
- Worker chạy ngầm → đọc từng message → INSERT DB → không ảnh hưởng Client

### Luồng Module 2

```
1. Client gửi: POST /api/upload (file CSV)

2. Flask API (app.py):
   - Đọc từng dòng CSV
   - Validate: order_id, product_id, quantity phải là số nguyên
   - Publish message JSON vào RabbitMQ queue "order_queue"
     {"order_id": 1, "product_id": 100, "quantity": 5}
   - Trả về: {"sent_to_queue": N, "skipped_rows": M}

3. RabbitMQ: lưu message trong queue, chờ Worker đến lấy

4. Worker (worker.py) chạy liên tục:
   - Lấy 1 message từ queue (prefetch_count=1)
   - Kiểm tra product_id có trong bảng products không
   - Kiểm tra order_id đã tồn tại chưa (tránh duplicate)
   - INSERT INTO orders ...
   - ACK → RabbitMQ xóa message khỏi queue
   - Nếu lỗi → NACK (không requeue, tránh loop vô hạn)
```

### Đảm bảo độ tin cậy

| Cơ chế | Ý nghĩa |
|---|---|
| `delivery_mode=2` | Message persistent — không mất nếu RabbitMQ restart |
| `durable=True` queue | Queue tồn tại sau khi RabbitMQ restart |
| `prefetch_count=1` | Worker xử lý 1 message, xong mới lấy cái tiếp theo |
| ACK sau khi INSERT | Nếu Worker crash trước khi ACK → message quay lại queue |
| NACK requeue=False | Tránh message lỗi bị retry vô hạn |

---

## 6. MODULE 4 — Kong Gateway

### Tại sao cần Kong?

Không có Kong: Client gọi thẳng Flask `localhost:5000` — không xác thực, không giới hạn.

Có Kong: Client chỉ biết `localhost:8000` — Flask ẩn hoàn toàn bên trong Docker.

### 5 thành phần Kong

**SERVICE** — Địa chỉ Flask bên trong Docker:
```
flask-order-service → http://flask-api:5000
```

**ROUTE** — URL nào Kong nhận và forward:
```
/api/upload  (POST) → forward đến Service
/health      (GET)  → forward đến Service
strip_path: false   → giữ nguyên path khi forward Flask
```

**PLUGIN: key-auth** — Xác thực API key:
```
Client gửi Header: apikey: team8-secret-api-key-2024
Kong tra PostgreSQL → tìm thấy → cho qua
Sai/thiếu → HTTP 401 Unauthorized
```

**PLUGIN: rate-limiting** — Giới hạn tốc độ:
```
Mỗi consumer: tối đa 10 request/phút, 100/giờ
Vượt ngưỡng → HTTP 429 Too Many Requests
Header response: X-RateLimit-Remaining-Minute: 7
```

**CONSUMER** — Người dùng đã đăng ký:
```
team8-client → key: team8-secret-api-key-2024
admin-user   → key: admin-master-key-noah
```

### Luồng request qua Kong

```
Client
  ↓ POST localhost:8000/api/upload
  ↓ Header: apikey: team8-secret-api-key-2024

[Kong nhận]
  ↓ key-auth: key hợp lệ? → Có → tiếp tục / Không → 401 DỪNG
  ↓ rate-limiting: < 10 req/min? → Có → tiếp tục / Không → 429 DỪNG
  ↓ Xóa header apikey (hide_credentials)

Flask API :5000
  ↓ Xử lý, push RabbitMQ
  ↓ Trả response

Kong → Client (kèm header X-RateLimit-*)
```

---

## 7. LUỒNG DỮ LIỆU HOÀN CHỈNH

### Trước khi chạy (chuẩn bị)
```
python src/main.py
  → Đọc inventory.csv (5001 dòng bẩn)
  → Làm sạch, gộp duplicate
  → Ghi clean_inventory.csv (201 sản phẩm)
  → Ghi logs/error.log
```

### Khởi động hệ thống
```
docker-compose up -d
  → MySQL start → đọc init.sql → tạo bảng products (stock=0) + orders (20k rows)
  → RabbitMQ start → tạo queue rỗng
  → Flask start → lắng nghe :5000
  → Worker start → kết nối RabbitMQ, chờ message
  → PostgreSQL start → Kong migration → tạo schema
  → Kong start → đọc config từ PostgreSQL → lắng nghe :8000 và :8001
```

### Cấu hình Kong
```
python setup_kong.py
  → Gọi Admin API :8001
  → Tạo Service (Flask address)
  → Tạo Routes (/api/upload, /health)
  → Bật key-auth plugin
  → Bật rate-limiting plugin
  → Tạo consumer team8-client + API key
  → Tạo consumer admin-user + API key
  → Kong lưu tất cả vào PostgreSQL
```

### Gửi đơn hàng (runtime)
```
1. Client: POST localhost:8000/api/upload + Header apikey + Body file.csv
2. Kong: Xác thực key → OK → Giới hạn tốc độ → OK → Forward Flask
3. Flask: Đọc CSV → Publish từng dòng vào RabbitMQ → Trả {"sent": N}
4. Worker: Lấy message → Validate → INSERT MySQL → ACK
5. MySQL: Lưu đơn hàng vào bảng orders
```

### Test
```
python test_kong.py
  Test 1: GET /health, không có key          → Kong 401 ✅
  Test 2: GET /health, key sai               → Kong 401 ✅
  Test 3: GET /health, key đúng              → Flask 200 ✅
  Test 4: POST /api/upload, key đúng + CSV   → Flask 200 ✅
  Test 5: POST /api/upload, không có key     → Kong 401 ✅
  Test 6: GET /health, 12 lần liên tiếp      → lần 11: Kong 429 ✅
```

---

## 8. FIX LỖI 404 (strip_path)

**Nguyên nhân:** Kong mặc định `strip_path=true` → khi client gọi `/health`,
Kong xóa prefix `/health` → forward Flask chỉ còn `/` → Flask không có route `/` → 404.

**Fix:** Thêm `strip_path: false` vào Routes → Kong giữ nguyên `/health` khi forward.

Đã fix trong `setup_kong.py` và `module4_learn.py`. Để áp dụng:
```powershell
docker-compose down -v    # Xóa volume (reset Kong DB)
docker-compose up -d      # Khởi động lại
# Chờ 60 giây
python setup_kong.py      # Cấu hình lại Kong (với strip_path=false)
python test_kong.py       # Tất cả 6 test phải PASS
```
