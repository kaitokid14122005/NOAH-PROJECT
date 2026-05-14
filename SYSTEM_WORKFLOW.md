# Giải thích Luồng Hệ thống (System Workflow & Architecture)

Tài liệu này giải thích chi tiết về cách vận hành, cấu trúc các lớp và cơ chế xử lý dữ liệu của dự án NOAH.

---

## 1. Kiến trúc phân lớp (Layered Architecture)

Hệ thống được chia thành 3 tầng chính để đảm bảo tính module hóa và dễ mở rộng:

### A. Tầng Middleware (Lớp trung gian)
Đây là lớp bảo vệ và điều phối toàn bộ hệ thống.
*   **Kong API Gateway:** Điểm tiếp nhận duy nhất cho mọi yêu cầu từ Client. Nó đóng vai trò là "người điều phối giao thông".
*   **Auth Middleware:** Xác thực danh tính người dùng (API Key). Đảm bảo chỉ người dùng hợp lệ mới có thể truy cập.
*   **Logging Middleware:** Ghi lại nhật ký các yêu cầu để theo dõi và sửa lỗi.
*   **Caching Middleware:** Lưu trữ tạm thời các kết quả trả về thường xuyên để tăng tốc độ phản hồi.

### B. Tầng Service (Lớp nghiệp vụ)
Nơi chứa logic xử lý cốt lõi của ứng dụng.
*   **Python Data Processor (Flask API):** Tiếp nhận dữ liệu từ người dùng, kiểm tra tính hợp lệ sơ bộ và phân phối công việc.
*   **RabbitMQ (Message Broker):** "Hộp thư" trung gian giúp các service giao tiếp bất đồng bộ, tránh làm nghẽn hệ thống khi có lượng lớn dữ liệu.
*   **Worker:** Thành phần xử lý ngầm, chịu trách nhiệm thực hiện các tác vụ nặng như ghi dữ liệu vào database.

### C. Tầng Data (Lớp dữ liệu)
Nơi lưu trữ bền vững thông tin.
*   **MySQL (Main DB):** Lưu trữ dữ liệu nghiệp vụ chính (Sản phẩm, Đơn hàng).
*   **PostgreSQL (Support DB):** Lưu trữ dữ liệu cấu hình cho Kong Gateway.

---

## 2. Luồng chạy của hệ thống (System Workflow)

Lộ trình của một yêu cầu (Request) từ khi bắt đầu đến khi hoàn tất:

1.  **Gửi yêu cầu:** Client gửi yêu cầu kèm API Key tới `localhost:8000` (Kong).
2.  **Kiểm soát:** Kong kiểm tra API Key và giới hạn tốc độ (Rate Limiting). Nếu hợp lệ, nó xóa API Key khỏi header và chuyển tiếp (forward) yêu cầu tới Flask API.
3.  **Tiếp nhận:** Flask API nhận dữ liệu (ví dụ: file CSV), kiểm tra định dạng và đẩy từng dòng dữ liệu vào hàng đợi **RabbitMQ**.
4.  **Phản hồi nhanh:** Ngay sau khi đẩy vào hàng đợi thành công, Flask trả về kết quả cho Client (ví dụ: "Đã nhận đơn hàng").
5.  **Xử lý ngầm:** **Worker** lấy dữ liệu từ RabbitMQ, kiểm tra sự tồn tại của sản phẩm trong MySQL và thực hiện lệnh `INSERT` vào bảng `orders`.
6.  **Hoàn tất:** Dữ liệu được lưu trữ an toàn trong MySQL.

---

## 3. Cơ chế xử lý: Đồng bộ hay Bất đồng bộ?

Hệ thống sử dụng mô hình **Hybrid (Kết hợp)** để tối ưu hóa hiệu suất:

### Đồng bộ (Synchronous)
*   **Áp dụng:** Giao tiếp giữa **Client ↔ Kong ↔ Flask API**.
*   **Mục đích:** Người dùng nhận được phản hồi ngay lập tức về trạng thái yêu cầu của họ (Thành công/Thất bại trong việc gửi dữ liệu).

### Bất đồng bộ (Asynchronous)
*   **Áp dụng:** Luồng xử lý dữ liệu giữa **Flask API ↔ RabbitMQ ↔ Worker ↔ MySQL**.
*   **Mục đích:** 
    *   Giúp hệ thống không bị treo khi xử lý hàng nghìn dòng dữ liệu cùng lúc.
    *   Tăng khả năng chịu tải: Nếu Database quá tải, dữ liệu sẽ tạm thời nằm trong RabbitMQ chờ Worker xử lý dần dần.
    *   Tách biệt trách nhiệm: Flask chỉ lo nhận tin, Worker mới lo việc thực thi.

---
*Tài liệu được soạn thảo để giải thích chi tiết cấu trúc hệ thống NOAH.*
