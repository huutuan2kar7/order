# 🍜 BẾP VIỆT ONLINE - WEBSITE ĐẶT MÓN ĂN & QUẢN LÝ ĐƠN HÀNG TRỰC TUYẾN

Hệ thống Website thương mại điện tử chuyên ngành ẩm thực hoàn chỉnh được xây dựng nhằm đáp ứng toàn bộ các yêu cầu của đồ án / bài tập lớn.

---

## 📌 BẢNG ĐỐI CHIẾU ĐÁP ỨNG YÊU CẦU ĐỀ BÀI

| Yêu cầu đề bài | Thành phần & Triển khai trong ứng dụng |
| :--- | :--- |
| **Dạng ứng dụng: Website** | Xây dựng ứng dụng Web chuẩn MVC với **Flask**, giao diện responsive chuẩn cho máy tính và điện thoại di động (Bootstrap 5 + CSS3). |
| **Ngôn ngữ: Python** | Lập trình toàn bộ Backend, Bộ định tuyến (Routing), Quản lý CSDL (ORM), Xử lý logic và API. |
| **Thư viện: NumPy** | • Tính giá trị đơn hàng trung bình (`np.mean`)<br>• Tính trung vị giá trị đơn (`np.median`)<br>• Tính độ lệch chuẩn chi tiêu (`np.std`)<br>• Phân vị chi tiêu khách hàng Q1 (25%), Q3 (75%), VIP (90%) (`np.percentile`)<br>• Tính toán đường xu hướng hồi quy tuyến tính dự báo doanh thu (`np.polyfit` & `np.poly1d`). |
| **Thư viện: Pandas** | • Chuyển đổi dữ liệu CSDL thành DataFrame (`pd.DataFrame`)<br>• Nhóm và tổng hợp doanh thu theo ngày/tháng (`groupby('date').agg(...)`)<br>• Thống kê Top món ăn bán chạy nhất (`top_foods`)<br>• Phân tích cơ cấu danh mục món (`cat_share`)<br>• Phân tích số lượng đơn theo 24 khung giờ (`dt.hour`). |
| **Thư viện: Matplotlib** | Vẽ và xuất trực tiếp 5 đồ thị chuẩn cao độ phân giải (Base64 Web Render):<br>1. *Xu hướng Doanh thu theo Ngày & Đường xu hướng hồi quy tuyến tính (tự động cập nhật)*<br>2. *Top Món Ăn Bán Chạy Nhất (Horizontal Bar)*<br>3. *Cơ Cấu Tỷ Trọng Danh Mục Món (Donut Chart)*<br>4. *Phân Bố 24 Khung Giờ Đặt Hàng (Highlight Cao Điểm Trưa/Tối)*<br>5. *Phân Phối Giá Trị Đơn Hàng (Boxplot Phân Vị)*. |
| **Giao diện đồ họa (GUI)** | • **Khách hàng:** Trang chủ thực đơn động, bộ lọc danh mục, tìm kiếm theo tên món, giỏ hàng trượt (Offcanvas Drawer), thanh toán trực quan, màn hình theo dõi đơn hàng với hiệu ứng Stepper tiến trình thời gian thực.<br>• **Quản trị (Admin):** Bảng KPI thống kê, **tính năng tự nhập đơn hàng thủ công**, quản lý đơn hàng (đổi trạng thái 1-click), CRUD thực đơn (thêm/sửa/xóa món, ẩn/hiện còn hàng/hết hàng), trang phân tích báo cáo đồ thị chuyên sâu. |
| **Khuyến khích: CSDL MySQL** | • Cung cấp đầy đủ file cấu hình kết nối CSDL MySQL qua `PyMySQL` và `SQLAlchemy`.<br>• Cung cấp file khởi tạo CSDL `mysql_schema.sql`.<br>• **Cơ chế Fallback thông minh:** Tự động chuyển sang SQLite nếu máy chưa cài/bật MySQL, giúp chạy ngay lập tức không bị lỗi. |
| **Khuyến khích: Truyền thông mạng** | • Kiến trúc Client-Server RESTful API (HTTP JSON).<br>• Cơ chế AJAX / Fetch API gửi nhận dữ liệu đơn hàng.<br>• Giao thức **Server-Sent Events (SSE)** tại endpoint `/api/orders/live-stream` giúp Dashboard của Bếp / Quản trị tự động nhận thông báo đơn hàng mới qua mạng theo thời gian thực mà không cần F5. |

---

## 🎯 CƠ CHẾ TỰ NHẬP ĐƠN & BIỂU ĐỒ TỰ CẬP NHẬT

Hệ thống **không cài đặt sẵn các đơn hàng ảo**. Khi mới khởi chạy, số lượng đơn hàng là **0 đơn**. Bạn có thể tự do nhập đơn theo 2 cách:

1. **Cách 1 - Khách hàng đặt món trên Website:**
   - Mở trang [http://127.0.0.1:5000/](http://127.0.0.1:5000/).
   - Chọn các món ăn bạn thích, bấm **"Thêm Món"** ➔ Mở giỏ hàng ➔ Điền họ tên, số điện thoại, địa chỉ ➔ Bấm **"Xác Nhận Đặt Món"**.
2. **Cách 2 - Quản trị viên tự nhập đơn thủ công:**
   - Đăng nhập trang Quản trị tại [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login), sau đó mở trang Quản lý đơn hàng hoặc Dashboard.
   - Bấm nút **"Tự Nhập Đơn Hàng Mới"**.
   - Bạn có thể tùy chọn: Tên khách hàng, số điện thoại, ngày giờ đặt món, chọn món ăn trong thực đơn, số lượng, phương thức thanh toán và trạng thái đơn (Hoàn thành, Đang nấu, Đang giao...).
   - Bấm **"Lưu Đơn & Cập Nhật Biểu Đồ"**.

👉 **Quan sát kết quả tự cập nhật:**  
Mở trang **Báo Cáo & Đồ Thị** tại [http://127.0.0.1:5000/admin/analytics](http://127.0.0.1:5000/admin/analytics). Ngay khi bạn nhập thêm đơn mới hoặc thay đổi trạng thái đơn (từ Chờ duyệt sang Hoàn thành, hoặc Hủy đơn), toàn bộ 5 biểu đồ Matplotlib và các chỉ số thống kê toán học của NumPy/Pandas sẽ **tự động tính toán lại và vẽ mới ngay tức thì**!

*(Nếu muốn xóa sạch toàn bộ đơn để nhập lại từ đầu, bạn chỉ cần bấm nút **"Xóa Hết Đơn"** tại trang Quản lý đơn hàng).*

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
food_ordering_app/
│
├── app.py                     # Entry point khởi chạy ứng dụng Flask & REST API
├── config.py                  # Cấu hình CSDL (MySQL / SQLite Fallback) & bảo mật
├── models.py                  # Cấu trúc CSDL SQLAlchemy (Category, FoodItem, Order, OrderItem)
├── analytics.py               # Phân tích dữ liệu & vẽ đồ thị (Pandas, Numpy, Matplotlib)
├── seed_data.py               # Dữ liệu thực đơn món ăn ban đầu (0 đơn hàng mặc định)
├── mysql_schema.sql           # File kịch bản CSDL MySQL thuần (Dùng cho MySQL Workbench / phpMyAdmin)
├── requirements.txt           # Danh sách các thư viện cần thiết
├── README.md                  # Tài liệu hướng dẫn sử dụng
│
├── static/
│   ├── css/
│   │   └── style.css          # Giao diện tùy chỉnh, hiệu ứng động & bố cục màu sắc
│   └── js/
│       ├── main.js            # Quản lý giỏ hàng phía Client, Lưu trữ localStorage
│       └── admin.js           # Xử lý tương tác phía bảng điều khiển quản trị
│
└── templates/
    ├── base.html              # Khung giao diện chuẩn (Header, Navigation, Giỏ trượt, Footer)
    ├── index.html             # Trang chủ: Thực đơn món ăn, Lọc danh mục, Tìm kiếm
    ├── cart.html              # Trang giỏ hàng & Thanh toán (Checkout)
    ├── order_success.html     # Xác nhận đặt hàng & Stepper tiến trình trực tiếp
    ├── track_order.html       # Tra cứu đơn hàng theo Mã và Số điện thoại
    └── admin/
        ├── login.html          # Đăng nhập khu vực quản trị
        ├── base_admin.html    # Khung giao diện Quản trị viên
        ├── dashboard.html     # Tổng quan & Nút tự nhập đơn nhanh
        ├── orders.html        # Quản lý đơn hàng, Modal tự nhập đơn & Xóa hết đơn
        ├── menu.html          # Quản lý thực đơn (Thêm món, Ẩn/Hiện, Xóa món)
        └── analytics.html     # Trang hiển thị 5 biểu đồ Matplotlib tự cập nhật theo đơn
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY ỨNG DỤNG

### 1. Chuẩn bị môi trường
Mở Terminal / PowerShell và chuyển đến thư mục dự án:
```bash
cd "C:\Users\Admin\.gemini\antigravity\scratch\food_ordering_app"
```

Cài đặt các thư viện cần thiết (nếu máy chưa có):
```bash
python -m pip install -r requirements.txt
```

### 2. Khởi chạy ứng dụng
Thiết lập mật khẩu quản trị và khóa phiên trong PowerShell (thay mật khẩu mẫu bằng giá trị riêng):
```powershell
$env:ADMIN_PASSWORD = "thay-bang-mat-khau-rieng"
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
```

Giữ `SECRET_KEY` ổn định giữa các lần chạy nếu muốn phiên đăng nhập hiện tại còn hiệu lực. Không đưa mật khẩu hoặc khóa này vào Git.

Chỉ cần chạy lệnh sau:
```bash
python app.py
```

### 3. Trải nghiệm trên trình duyệt
- **Giao diện Khách hàng (Tự chọn món & Đặt đơn):**
  👉 [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Đăng nhập Quản trị viên:**  
  👉 [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)
- **Giao diện Quản trị viên (Tự nhập đơn thủ công & Quản lý):**
  👉 [http://127.0.0.1:5000/admin/orders](http://127.0.0.1:5000/admin/orders)
- **Xem trực tiếp 5 Đồ thị Matplotlib / Pandas / Numpy tự cập nhật:**
  👉 [http://127.0.0.1:5000/admin/analytics](http://127.0.0.1:5000/admin/analytics)

Mặc định ứng dụng chỉ lắng nghe trên máy hiện tại và tắt Flask debug mode. Nếu cần demo qua mạng LAN, đặt `$env:HOST = "0.0.0.0"` trong PowerShell; không bật debug mode trên mạng dùng chung. Trang quản trị yêu cầu đăng nhập và các thao tác thay đổi dữ liệu được bảo vệ bằng CSRF token. Tra cứu đơn cần cả mã đơn và số điện thoại.
