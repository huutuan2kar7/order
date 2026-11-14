import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    # Cấu hình CSDL: Hỗ trợ linh hoạt cả MySQL và SQLite
    # Nếu muốn dùng MySQL:
    # 1. Tạo database trong MySQL: CREATE DATABASE food_ordering_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    # 2. Đặt USE_MYSQL = True hoặc thiết lập biến môi trường USE_MYSQL=1
    USE_MYSQL = os.environ.get('USE_MYSQL', '0') in ('1', 'true', 'True')
    
    # Thông tin kết nối MySQL
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'food_ordering_db')
    
    MYSQL_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    
    # Đường dẫn CSDL SQLite mặc định
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'food_ordering.db')}"
    
    # Chọn URI phù hợp
    if USE_MYSQL:
        SQLALCHEMY_DATABASE_URI = MYSQL_URI
    else:
        SQLALCHEMY_DATABASE_URI = SQLITE_URI
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0').lower() in ('1', 'true')
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }
