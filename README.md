# 🌟 NOAH Project - CMU-CS 445 ZIS (Team 8)
**Integration Practice - Version 1.1**

Dự án NOAH giải quyết bài toán tích hợp hệ thống cho Noah Retail, xử lý dữ liệu hàng tồn kho từ file CSV (chứa dữ liệu "bẩn"), làm sạch và tích hợp qua pipeline bất đồng bộ sử dụng **Python, RabbitMQ, MySQL, PostgreSQL và Kong API Gateway**.

---

## 🛠️ Cấu trúc thư mục (Directory Structure)

```text
Group_Project Part 1/
├── data/                    ← Chứa file dữ liệu đầu vào (inventory.csv) và file init DB (init.sql)
├── kong/                    ← Cấu hình Kong Gateway (kong.yml)
├── logs/                    ← File log lỗi quá trình làm sạch dữ liệu
├── output/                  ← Nơi chứa file CSV sau khi làm sạch (clean_inventory.csv)
├── src/                     ← Mã nguồn Python
│   ├── app.py               ← Flask API (Nhận CSV, đẩy vào RabbitMQ)
│   ├── cleaner.py           ← Logic làm sạch dữ liệu CSV
│   ├── logger.py            ← Script ghi log lỗi
│   ├── main.py              ← Script chạy Module 1 (Làm sạch file)
│   └── worker.py            ← Worker (Đọc RabbitMQ, lưu vào MySQL)
├── docker-compose.yml       ← Cấu hình chạy toàn bộ hệ thống (MySQL, RabbitMQ, Flask, Worker, Kong)
├── Dockerfile.api           ← Môi trường chạy Flask API
├── Dockerfile.worker        ← Môi trường chạy Worker
├── requirements.txt         ← Các thư viện Python cần thiết
├── setup_kong.py            ← Script tự động cấu hình Kong Gateway
├── test_kong.py             ← Script test API qua Kong
└── README.md                ← Hướng dẫn này
```

---

## ⚙️ Yêu cầu hệ thống (Prerequisites)

Để chạy dự án, máy tính của bạn cần cài đặt:
1. **Python 3.10+**: Để chạy script làm sạch dữ liệu và cấu hình Kong.
2. **Docker & Docker Compose**: Để chạy các dịch vụ database, message broker và API Gateway.
3. **Git Bash hoặc PowerShell**: Để chạy các lệnh dòng lệnh.

---

## 🚀 Hướng dẫn chạy dự án từ A-Z

### BƯỚC 1: Clone dự án và cài đặt thư viện Python

Mở Terminal (PowerShell hoặc Git Bash) tại thư mục chứa dự án:

```powershell
# Di chuyển vào thư mục dự án (Thay đổi đường dẫn nếu bạn để ở nơi khác)
cd "d:\Group_Project Part 1"

# (Tùy chọn) Tạo môi trường ảo Python để không ảnh hưởng hệ thống
python -m venv venv
venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### BƯỚC 2: Chạy Module 1 (Làm sạch dữ liệu CSV)

Dữ liệu đầu vào nằm ở `data/inventory.csv` có nhiều dữ liệu lỗi. Chúng ta cần làm sạch nó.

```powershell
# Vẫn đang ở thư mục "d:\Group_Project Part 1"
python src/main.py
```

**Kết quả mong đợi:**
- Script chạy thành công và báo cáo số dòng đã sửa/bỏ qua.
- Một file mới được tạo ra tại: `output/clean_inventory.csv`.
- Các lỗi được ghi lại trong file: `logs/error.log`.

### BƯỚC 3: Khởi động hệ thống Docker (Module 2 & 4)

Chúng ta sẽ khởi động cơ sở dữ liệu (MySQL, PostgreSQL), RabbitMQ, Kong Gateway, Flask API và Worker.

```powershell
# Chạy Docker Compose (tải image và chạy ngầm)
docker-compose up -d --build
```
*Lưu ý: Quá trình này có thể mất 3-5 phút trong lần chạy đầu tiên để tải các Docker image.*

**Kiểm tra xem tất cả container đã chạy chưa:**
```powershell
docker-compose ps
```
Bạn phải thấy 6 container có trạng thái `Up` hoặc `running`:
- `noah-mysql`
- `noah-rabbitmq`
- `noah-flask-api`
- `noah-worker`
- `noah-kong-db`
- `noah-kong`

### BƯỚC 4: Cấu hình Kong API Gateway (Security)

Kong Gateway cần được cấu hình các service, route và plugin (Auth, Rate Limit). Script `setup_kong.py` sẽ làm việc này tự động.

```powershell
# Đợi khoảng 30-60 giây sau BƯỚC 3 để Kong khởi động hoàn toàn, sau đó chạy:
python setup_kong.py
```

**Kết quả mong đợi:** Các thông báo `✅ Service created`, `✅ Route created`, `✅ Key Auth enabled`, `✅ Rate Limiting enabled` hiện ra.

### BƯỚC 5: Chạy Test kiểm tra tích hợp

Bây giờ hệ thống đã hoàn thiện: Kong bảo vệ API, Flask nhận dữ liệu, RabbitMQ làm hàng đợi, Worker lưu vào MySQL. Hãy chạy script test:

```powershell
python test_kong.py
```

**Kết quả mong đợi:**
Các test case 1 đến 6 đều báo `[PASS]`. Test số 6 có thể sẽ báo lỗi 429 (Too Many Requests) - điều này là **ĐÚNG** vì Kong đã chặn do Rate Limiting.

---

## 🛠 Lệnh Debug và Khắc phục sự cố (Troubleshooting)

**1. Nếu `python src/main.py` báo lỗi "No such file or directory":**
Lý do là bạn đang đứng sai thư mục trên Terminal. Hãy chắc chắn bạn đang đứng ở thư mục gốc `d:\Group_Project Part 1` chứ không phải ở bên trong `src`.

**2. Nếu `setup_kong.py` báo lỗi "Connection Refused":**
Nghĩa là Kong Gateway trong Docker chưa khởi động xong. Chờ thêm 1 phút và chạy lại lệnh `python setup_kong.py`.

**3. Xem log để xem worker lưu dữ liệu vào database thành công hay không:**
```powershell
docker logs noah-worker -f
```
*(Bấm Ctrl+C để thoát khỏi chế độ xem log)*

**4. Xem dữ liệu đã vào MySQL chưa:**
```powershell
# Truy cập vào MySQL container
docker exec -it noah-mysql mysql -unoah_user -pnoah_pass noah_db

# Chạy lệnh SQL:
SELECT * FROM orders LIMIT 10;
exit
```

**5. Dừng và dọn dẹp hệ thống khi làm xong:**
```powershell
docker-compose down -v
```

### BƯỚC 6: Chạy Module 4 (Học về Kong Gateway)
```powershell
python module4_learn.py
```
