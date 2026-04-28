# Hướng Dẫn Test API NOAH Project Trên Postman Đầy Đủ

Tài liệu này hướng dẫn chi tiết cách kiểm thử toàn bộ luồng API của dự án NOAH thông qua **Kong API Gateway**, bao gồm kiểm tra bảo mật (API Key), Rate Limiting và chức năng xử lý đơn hàng cốt lõi (Upload CSV).

> [!IMPORTANT]
> Trước khi bắt đầu, hãy đảm bảo tất cả các container Docker đang chạy (MySQL, RabbitMQ, Flask API, Kong, Kong Database).
> Lệnh khởi động: `docker-compose up -d`

---

## 1. Chuẩn Bị Postman Environment

Để không phải nhập lại URL nhiều lần, bạn nên tạo Environment Variable trong Postman:

1. Mở Postman, chọn mục **Environments** ở thanh sidebar trái.
2. Bấm **Create Environment** (hoặc dấu `+`), đặt tên là `NOAH Local`.
3. Thêm biến sau:
   - Variable: `base_url`
   - Initial value: `http://localhost:8000` (Đây là port của Kong Proxy)
4. Bấm **Save**. Nhìn lên góc phải trên cùng của Postman, chọn environment `NOAH Local` từ dropdown.

---

## 2. Kịch Bản Test 1: Kiểm tra Bảo Mật (Không dùng API Key)

Mục đích: Đảm bảo Kong Gateway chặn các request không hợp lệ.

- **Method**: `GET`
- **URL**: `{{base_url}}/health`
- **Headers**: *(Không thêm gì cả)*
- **Bấm Send**

**Kết quả mong đợi (Expected Result):**
- **Status Code**: `401 Unauthorized`
- **Body**: 
  ```json
  {
      "message": "No API key found in request"
  }
  ```

---

## 3. Kịch Bản Test 2: Kiểm tra Health Check (Có API Key)

Mục đích: Đảm bảo Flask Backend đang hoạt động và Kong chuyển tiếp request thành công khi có API Key đúng.

- **Method**: `GET`
- **URL**: `{{base_url}}/health`
- **Headers**:
  - Key: `apikey`
  - Value: `team8-secret-api-key-2024` (hoặc `admin-master-key-noah`)
- **Bấm Send**

**Kết quả mong đợi (Expected Result):**
- **Status Code**: `200 OK`
- **Body**:
  ```json
  {
      "service": "flask-api",
      "status": "ok"
  }
  ```

> [!TIP]
> **Cách xem Rate Limit Header**:
> Sau khi Send, hãy mở tab **Headers** trong phần *Response* ở dưới, bạn sẽ thấy các thông số Rate Limit mà Kong trả về:
> - `X-RateLimit-Limit-Minute`: 10
> - `X-RateLimit-Remaining-Minute`: 9

---

## 4. Kịch Bản Test 3: Xử lý file CSV Đơn Hàng (Upload File)

Mục đích: Kiểm tra chức năng chính của Module 2 (Flask xử lý CSV và đẩy vào RabbitMQ).

- **Method**: `POST`
- **URL**: `{{base_url}}/api/upload`
- **Headers**:
  - Key: `apikey`
  - Value: `team8-secret-api-key-2024`
- **Body**: 
  1. Chọn tab **Body** (dưới thanh URL)
  2. Chọn mục **form-data**
  3. Ở cột *Key*, gõ `file` -> Rê chuột vào chữ `file` đó, sẽ hiện ra dropdown dạng `Text/File` -> Đổi từ `Text` sang `File`.
  4. Ở cột *Value*, sẽ xuất hiện nút **Select Files**. Bấm vào đó và chọn file `data/inventory.csv` từ thư mục dự án của bạn (hoặc tạo một file `.csv` có header `order_id,product_id,quantity`).
- **Bấm Send**

**Kết quả mong đợi (Expected Result):**
- **Status Code**: `200 OK`
- **Body**:
  ```json
  {
      "message": "CSV processed successfully",
      "sent_to_queue": <số_lượng_record>,
      "skipped_rows": <số_lỗi_nếu_có>
  }
  ```

---

## 5. Kịch Bản Test 4: Kiểm tra Rate Limiting (Chống Spam)

Mục đích: Đảm bảo Kong Gateway Gateway chặn người dùng spam request quá 10 lần/phút (theo cấu hình trong `kong.yml`).

- Sử dụng lại Request ở **Kịch Bản 2** (`GET {{base_url}}/health`).
- Bấm nút **Send liên tục 11 lần** một cách nhanh chóng.

**Kết quả mong đợi (ở lần bấm thứ 11):**
- **Status Code**: `429 Too Many Requests`
- **Body**:
  ```json
  {
      "message": "API rate limit exceeded"
  }
  ```
- Phải đợi 1 phút sau bạn mới có thể gọi API trở lại.

---

## 6. Kịch Bản Test 5: Xác minh Backend Worker (Tùy chọn)

Sau khi upload CSV thành công ở Kịch Bản 3, bạn có thể kiểm tra xem hệ thống ngầm có hoạt động đúng không:

1. **Kiểm tra RabbitMQ**:
   - Mở trình duyệt: `http://localhost:15672/`
   - Đăng nhập: User `guest` / Pass `guest`
   - Vào tab **Queues**, tìm `order_queue` xem message có đang được xử lý không (Spike lên rồi về 0 tức là Worker đã tiêu thụ).
2. **Kiểm tra Database**:
   - Mở DBeaver/DataGrip kết nối vào MySQL (`localhost:3306`, user: `noah_user`, pass: `noah_pass`).
   - Query: `SELECT * FROM noah_db.orders;` để xem đơn hàng từ CSV đã được Insert thành công vào Database chưa.
