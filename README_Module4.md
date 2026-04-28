# NOAH Project - Module 4: Security & Governance
## Kong Gateway Setup Guide

---

## 📁 Cấu trúc file Module 4

```
Group_Project Part 1/
├── docker-compose.yml       ← Toàn bộ hệ thống (Kong + Flask + MySQL + RabbitMQ)
├── kong/
│   └── kong.yml             ← Declarative config Kong
├── Dockerfile.api           ← Build Flask API
├── Dockerfile.worker        ← Build Worker
├── requirements.txt         ← Python dependencies
├── setup_kong.py            ← Script cấu hình Kong tự động
├── test_kong.py             ← Script test Kong
└── src/
    ├── app.py               ← Flask API
    └── worker.py            ← Queue Consumer
```

---

## 🚀 Hướng dẫn chạy từng bước

### Bước 1: Kiểm tra Docker đã cài chưa
```powershell
docker --version
docker-compose --version
```

### Bước 2: Khởi động toàn bộ hệ thống
```powershell
cd "d:\Group_Project Part 1"
docker-compose up -d --build
```

> Lần đầu chạy sẽ mất 3-5 phút để pull image Kong (~150MB)

### Bước 3: Kiểm tra tất cả container đang chạy
```powershell
docker-compose ps
```
Kết quả mong đợi:
```
NAME                    STATUS
noah-mysql              running
noah-rabbitmq           running
noah-flask-api          running
noah-worker             running
noah-kong-db            running
noah-kong               running
```

### Bước 4: Cấu hình Kong Gateway
```powershell
pip install requests
python setup_kong.py
```

### Bước 5: Chạy Test Suite
```powershell
python test_kong.py
```

---

## 🔐 Kiến trúc bảo mật Module 4

```
Client
  │
  │  POST /api/upload
  │  Header: apikey: team8-secret-api-key-2024
  ▼
┌─────────────────────────────────────────┐
│         Kong Gateway :8000              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  Plugin 1: Key Authentication   │    │
│  │  • Kiểm tra header "apikey"     │    │
│  │  • Từ chối nếu key không hợp lệ │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  Plugin 2: Rate Limiting        │    │
│  │  • Max 10 req/phút              │    │
│  │  • Max 100 req/giờ              │    │
│  │  • Trả về 429 nếu vượt giới hạn │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  Reverse Proxy                  │    │
│  │  • Forward đến Flask :5000      │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
  │
  ▼
Flask API :5000  →  RabbitMQ  →  Worker  →  MySQL
```

---

## 🧪 Test Cases Module 4

| Test | Request | API Key | Expected | Mô tả |
|------|---------|---------|----------|-------|
| 1 | GET /health | ❌ Không có | 401 | Unauthorized |
| 2 | GET /health | ❌ Sai key | 401 | Invalid credentials |
| 3 | GET /health | ✅ Hợp lệ | 200 | Success |
| 4 | POST /api/upload | ✅ Hợp lệ | 200 | Upload CSV thành công |
| 5 | POST /api/upload | ❌ Không có | 401 | Unauthorized |
| 6 | GET /health x12 | ✅ Hợp lệ | 429 | Rate limit triggered |

---

## 🔑 API Keys

| Consumer | API Key | Quyền |
|----------|---------|-------|
| team8-client | `team8-secret-api-key-2024` | Upload CSV, Health check |
| admin-user | `admin-master-key-noah` | Toàn quyền |

---

## 🌐 Endpoints

| Endpoint | Port | Mô tả |
|----------|------|-------|
| Kong Proxy | `http://localhost:8000` | CLIENT gửi request vào đây |
| Kong Admin | `http://localhost:8001` | Quản lý Kong config |
| Flask Direct | `http://localhost:5000` | Bypass Kong (chỉ debug) |
| RabbitMQ UI | `http://localhost:15672` | guest/guest |

---

## 🛠️ Lệnh debug hữu ích

```powershell
# Xem logs Kong
docker logs noah-kong -f

# Xem logs Flask API
docker logs noah-flask-api -f

# Xem logs Worker
docker logs noah-worker -f

# Gửi request test thủ công
curl -X GET http://localhost:8000/health `
     -H "apikey: team8-secret-api-key-2024"

# Upload CSV thủ công
curl -X POST http://localhost:8000/api/upload `
     -H "apikey: team8-secret-api-key-2024" `
     -F "file=@data/orders_test.csv"

# Kiểm tra list routes
curl http://localhost:8001/routes

# Kiểm tra list plugins
curl http://localhost:8001/plugins

# Dừng tất cả
docker-compose down
```

---

## ⚠️ Troubleshooting

**Kong không khởi động được?**
```powershell
docker logs noah-kong-migration
docker logs noah-kong
```

**Flask không kết nối được RabbitMQ?**
```powershell
docker logs noah-flask-api
# Chờ RabbitMQ sẵn sàng, Flask tự retry 5 lần
```

**setup_kong.py báo lỗi connection?**
```powershell
# Đợi Kong sẵn sàng (khoảng 30-60s sau docker-compose up)
# Sau đó chạy lại setup_kong.py
```

# 1. Khởi động tất cả container
docker-compose up -d --build

# 2. Chờ ~60s rồi cấu hình Kong
python setup_kong.py

# 3. Chạy test suite
python test_kong.py
