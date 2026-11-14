import os
import sys
import time
import json
import math
import secrets
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, abort, render_template, request, jsonify, redirect, url_for, flash, Response, session
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from config import Config
from models import db, Category, FoodItem, Order, OrderItem
from seed_data import init_seed_data
import analytics

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.config.from_object(Config)

if Config.USE_MYSQL:
    probe_engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    try:
        with probe_engine.connect():
            pass
    except OperationalError as e:
        print(f"[Database Warning] Không thể kết nối tới MySQL ({e}). Chuyển sang SQLite nội bộ...")
        app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLITE_URI
    finally:
        probe_engine.dispose()

db.init_app(app)
with app.app_context():
    db.create_all()
    init_seed_data()
    print(f"[Database] Đang kết nối tới: {app.config['SQLALCHEMY_DATABASE_URI']}")

if not Config.ADMIN_PASSWORD:
    print("[Admin Warning] Chưa đặt ADMIN_PASSWORD; khu vực quản trị sẽ không cho đăng nhập.")
if not os.environ.get('SECRET_KEY'):
    print("[Security Warning] Chưa đặt SECRET_KEY; phiên đăng nhập sẽ hết hiệu lực khi khởi động lại.")


def _is_admin_request():
    return (
        request.path.startswith('/admin')
        or request.path.startswith('/api/admin/')
        or request.path == '/api/orders/live-stream'
    )


@app.before_request
def protect_admin_routes():
    if not _is_admin_request():
        return None

    if request.endpoint != 'admin_login' and not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        expected_token = session.get('_csrf_token')
        submitted_token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
        if (
            not expected_token
            or not submitted_token
            or not secrets.compare_digest(expected_token, submitted_token)
        ):
            abort(400, description='Yêu cầu không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang.')
    return None


@app.context_processor
def inject_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return {'csrf_token': session['_csrf_token']}


def generate_order_code(created_at=None):
    timestamp = created_at or datetime.now()
    return f"ORD-{timestamp.strftime('%Y%m%d')}-{secrets.token_hex(8).upper()}"


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        admin_password = app.config.get('ADMIN_PASSWORD')
        if not admin_password:
            return render_template(
                'admin/login.html',
                error='Chưa cấu hình ADMIN_PASSWORD trên máy chủ.'
            ), 503
        if secrets.compare_digest(request.form.get('password', ''), admin_password):
            session.clear()
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/login.html', error='Mật khẩu không chính xác.'), 401

    return render_template('admin/login.html')


@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# Format tiền tệ VNĐ trong template Jinja2
@app.template_filter('format_currency')
def format_currency(value):
    try:
        val = float(value)
        return f"{val:,.0f} đ".replace(',', '.')
    except (ValueError, TypeError):
        return f"{value} đ"

# ==============================================================================
# 1. KHÁCH HÀNG (CUSTOMER FACING ROUTES)
# ==============================================================================

@app.route('/')
def index():
    """Trang chủ hiển thị thực đơn, tìm kiếm và thêm vào giỏ"""
    categories = Category.query.all()
    selected_category = request.args.get('category', 'all')
    search_query = request.args.get('q', '').strip()
    
    query = FoodItem.query.filter_by(is_available=True)
    if selected_category != 'all':
        cat = Category.query.filter_by(slug=selected_category).first()
        if cat:
            query = query.filter_by(category_id=cat.id)
            
    if search_query:
        query = query.filter(FoodItem.name.ilike(f"%{search_query}%"))
        
    foods = query.all()
    return render_template('index.html', 
                           categories=categories, 
                           foods=foods, 
                           selected_category=selected_category,
                           search_query=search_query)

@app.route('/cart')
def cart():
    """Trang giỏ hàng & thanh toán (Checkout)"""
    return render_template('cart.html')

@app.route('/order-success/<order_code>')
def order_success(order_code):
    """Trang xác nhận đặt hàng thành công & theo dõi trạng thái đơn hàng"""
    accessible_orders = session.get('order_access_codes', [])
    if not isinstance(accessible_orders, list) or order_code not in accessible_orders:
        abort(404)
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    return render_template('order_success.html', order=order)

@app.route('/track', methods=['GET', 'POST'])
def track_order():
    """Tra cứu đơn hàng bằng mã đơn và số điện thoại xác nhận"""
    order = None
    query = request.args.get('code', '').strip()
    phone = request.args.get('phone', '').strip()
    searched = bool(query and phone)
    
    if searched:
        order = Order.query.filter_by(
            order_code=query,
            customer_phone=phone
        ).first()
        
    return render_template(
        'track_order.html',
        order=order,
        query=query,
        phone=phone,
        searched=searched
    )

# ==============================================================================
# 2. REST API (TRUYỀN THÔNG MẠNG / NETWORK COMMUNICATION)
# ==============================================================================

@app.route('/api/order/create', methods=['POST'])
def api_create_order():
    """API Tạo đơn hàng mới từ Web Client qua giao thức HTTP POST JSON"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'success': False, 'message': 'Dữ liệu đơn hàng không hợp lệ!'}), 400

    items = data.get('items')
    if not isinstance(items, list) or not items or len(items) > 50:
        return jsonify({'success': False, 'message': 'Giỏ hàng trống hoặc dữ liệu không hợp lệ!'}), 400
        
    customer_name = data.get('customer_name')
    customer_phone = data.get('customer_phone')
    customer_address = data.get('customer_address')
    notes = data.get('notes', '')
    payment_method = data.get('payment_method', 'COD')
    
    if not all(isinstance(value, str) for value in (
        customer_name, customer_phone, customer_address, notes
    )):
        return jsonify({'success': False, 'message': 'Thông tin khách hàng không hợp lệ!'}), 400

    customer_name = customer_name.strip()
    customer_phone = customer_phone.strip()
    customer_address = customer_address.strip()
    notes = notes.strip()
    if (
        not customer_name
        or len(customer_name) > 100
        or not customer_phone
        or len(customer_phone) > 20
        or not customer_address
        or len(customer_address) > 255
        or len(notes) > 2000
    ):
        return jsonify({'success': False, 'message': 'Vui lòng điền đầy đủ Họ tên, SĐT và Địa chỉ giao hàng!'}), 400

    valid_payment_methods = {'COD', 'BANK_TRANSFER', 'MOMO'}
    if not isinstance(payment_method, str) or payment_method not in valid_payment_methods:
        return jsonify({'success': False, 'message': 'Phương thức thanh toán không hợp lệ!'}), 400

    normalized_items = []
    for item in items:
        if not isinstance(item, dict):
            return jsonify({'success': False, 'message': 'Danh sách món ăn không hợp lệ!'}), 400
        food_id = item.get('id')
        quantity = item.get('quantity', 1)
        if (
            isinstance(food_id, bool)
            or not isinstance(food_id, int)
            or isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 1
            or quantity > 100
        ):
            return jsonify({'success': False, 'message': 'Món ăn hoặc số lượng không hợp lệ!'}), 400
        normalized_items.append((food_id, quantity))

    foods = FoodItem.query.filter(
        FoodItem.id.in_({food_id for food_id, _ in normalized_items}),
        FoodItem.is_available.is_(True)
    ).all()
    foods_by_id = {food.id: food for food in foods}
    if any(food_id not in foods_by_id for food_id, _ in normalized_items):
        return jsonify({
            'success': False,
            'message': 'Có món không tồn tại hoặc hiện đã hết hàng. Vui lòng tải lại thực đơn.'
        }), 400

    order_code = generate_order_code()
    
    new_order = Order(
        order_code=order_code,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        notes=notes,
        payment_method=payment_method,
        status='pending',
        total_price=0.0
    )
    db.session.add(new_order)
    db.session.flush()
    
    total = 0.0
    for food_id, quantity in normalized_items:
        food = foods_by_id[food_id]
        subtotal = food.price * quantity
        total += subtotal
        order_item = OrderItem(
            order_id=new_order.id,
            food_item_id=food.id,
            food_name=food.name,
            quantity=quantity,
            unit_price=food.price,
            subtotal=subtotal
        )
        db.session.add(order_item)

    if total <= 0 or not math.isfinite(total):
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Tổng tiền đơn hàng không hợp lệ!'}), 400
            
    new_order.total_price = total
    db.session.commit()
    accessible_orders = session.get('order_access_codes', [])
    if not isinstance(accessible_orders, list):
        accessible_orders = []
    session['order_access_codes'] = (accessible_orders + [order_code])[-20:]
    
    return jsonify({
        'success': True,
        'message': 'Đặt hàng thành công!',
        'order_code': order_code,
        'order_id': new_order.id,
        'total': total
    })

@app.route('/api/order/<order_code>', methods=['GET'])
def api_get_order_status(order_code):
    """API Tra cứu trạng thái đơn hàng (Polling qua mạng)"""
    order = Order.query.filter_by(order_code=order_code).first()
    if not order:
        return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng!'}), 404
    return jsonify({'success': True, 'order': {'status': order.status}})

@app.route('/api/orders/live-stream')
def api_orders_live_stream():
    """Server-Sent Events (SSE) phát thông báo đơn hàng mới qua mạng theo thời gian thực"""
    def event_stream():
        with app.app_context():
            latest_order = Order.query.order_by(Order.id.desc()).first()
            last_id = latest_order.id if latest_order else 0

        while True:
            with app.app_context():
                new_orders = Order.query.filter(
                    Order.id > last_id
                ).order_by(Order.id.asc()).limit(100).all()
                payloads = [
                    json.dumps({
                        'event': 'new_order',
                        'order': {
                            'order_code': order.order_code,
                            'customer_name': order.customer_name,
                            'total_price': order.total_price
                        }
                    })
                    for order in new_orders
                ]
                if new_orders:
                    last_id = new_orders[-1].id

            if payloads:
                for payload in payloads:
                    yield f"data: {payload}\n\n"
            else:
                yield ': keep-alive\n\n'
            time.sleep(3)
            
    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

# ==============================================================================
# 3. QUẢN TRỊ VIÊN (ADMIN DASHBOARD, MANUAL ORDERS, ANALYTICS)
# ==============================================================================

@app.route('/admin')
def admin_dashboard():
    """Bảng điều khiển tổng quan cho Quản trị viên"""
    data = analytics.get_analytics_data()
    kpis = data['kpis']
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    pending_count = Order.query.filter_by(status='pending').count()
    confirmed_count = Order.query.filter_by(status='confirmed').count()
    cooking_count = Order.query.filter_by(status='cooking').count()
    delivering_count = Order.query.filter_by(status='delivering').count()
    
    trend_chart = analytics.generate_revenue_trend_chart(data['daily_rev'])
    foods = FoodItem.query.filter_by(is_available=True).all()
    
    return render_template('admin/dashboard.html',
                           kpis=kpis,
                           recent_orders=recent_orders,
                           pending_count=pending_count,
                           confirmed_count=confirmed_count,
                           cooking_count=cooking_count,
                           delivering_count=delivering_count,
                           trend_chart=trend_chart,
                           foods=foods)

@app.route('/admin/orders')
def admin_orders():
    """Trang quản lý đơn hàng: Xem danh sách, tạo đơn thủ công, đổi trạng thái"""
    status_filter = request.args.get('status', 'all')
    query = Order.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    orders = query.order_by(Order.created_at.desc()).all()
    
    status_counts = {
        'all': Order.query.count(),
        'pending': Order.query.filter_by(status='pending').count(),
        'confirmed': Order.query.filter_by(status='confirmed').count(),
        'cooking': Order.query.filter_by(status='cooking').count(),
        'delivering': Order.query.filter_by(status='delivering').count(),
        'completed': Order.query.filter_by(status='completed').count(),
        'cancelled': Order.query.filter_by(status='cancelled').count()
    }
    
    foods = FoodItem.query.filter_by(is_available=True).all()
    
    return render_template('admin/orders.html', 
                           orders=orders, 
                           status_filter=status_filter,
                           status_counts=status_counts,
                           foods=foods)

@app.route('/admin/orders/create', methods=['POST'])
def admin_create_order_manual():
    """
    Tính năng cho phép Quản trị viên TỰ NHẬP ĐƠN HÀNG THỦ CÔNG:
    Có thể tự chọn món ăn, số lượng, khách hàng, ngày giờ và trạng thái (ví dụ đã hoàn thành)
    Đồ thị và chỉ số phân tích sẽ tự động cập nhật ngay lập tức!
    """
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    customer_address = request.form.get('customer_address', '').strip()
    notes = request.form.get('notes', '').strip()
    payment_method = request.form.get('payment_method', 'COD')
    status = request.form.get('status', 'completed')
    order_date_str = request.form.get('order_date', '')
    food_ids = request.form.getlist('food_id[]')
    quantities = request.form.getlist('quantity[]')
    valid_statuses = {'pending', 'confirmed', 'cooking', 'delivering', 'completed'}
    valid_payment_methods = {'COD', 'BANK_TRANSFER', 'MOMO'}
    
    if (
        not customer_name
        or len(customer_name) > 100
        or not customer_phone
        or len(customer_phone) > 20
        or len(customer_address) > 255
        or len(notes) > 2000
    ):
        flash('Vui lòng nhập thông tin khách hàng hợp lệ!', 'danger')
        return redirect(request.referrer or url_for('admin_orders'))

    if (
        status not in valid_statuses
        or payment_method not in valid_payment_methods
        or not food_ids
        or len(food_ids) > 50
        or len(food_ids) != len(quantities)
    ):
        flash('Trạng thái, phương thức thanh toán hoặc danh sách món không hợp lệ!', 'danger')
        return redirect(request.referrer or url_for('admin_orders'))

    normalized_items = []
    for food_id, quantity_text in zip(food_ids, quantities):
        try:
            parsed_food_id = int(food_id)
            quantity = int(quantity_text)
        except (ValueError, TypeError):
            flash('Mã món ăn hoặc số lượng không hợp lệ!', 'danger')
            return redirect(request.referrer or url_for('admin_orders'))
        if parsed_food_id <= 0 or quantity < 1 or quantity > 100:
            flash('Số lượng món phải nằm trong khoảng 1 đến 100!', 'danger')
            return redirect(request.referrer or url_for('admin_orders'))
        normalized_items.append((parsed_food_id, quantity))

    foods = FoodItem.query.filter(
        FoodItem.id.in_({food_id for food_id, _ in normalized_items}),
        FoodItem.is_available.is_(True)
    ).all()
    foods_by_id = {food.id: food for food in foods}
    if any(food_id not in foods_by_id for food_id, _ in normalized_items):
        flash('Có món không tồn tại hoặc hiện đã hết hàng. Vui lòng kiểm tra lại.', 'danger')
        return redirect(request.referrer or url_for('admin_orders'))

    if order_date_str:
        try:
            created_at = datetime.strptime(order_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Thời gian đặt món không hợp lệ!', 'danger')
            return redirect(request.referrer or url_for('admin_orders'))
    else:
        created_at = datetime.utcnow()
        
    order_code = generate_order_code(created_at)
    
    new_order = Order(
        order_code=order_code,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address or 'Nhận tại quán',
        notes=notes,
        payment_method=payment_method,
        status=status,
        created_at=created_at,
        updated_at=created_at,
        total_price=0.0
    )
    db.session.add(new_order)
    db.session.flush()
    
    total = 0.0
    for food_id, quantity in normalized_items:
        food = foods_by_id[food_id]
        subtotal = food.price * quantity
        total += subtotal
        db.session.add(OrderItem(
            order_id=new_order.id,
            food_item_id=food.id,
            food_name=food.name,
            quantity=quantity,
            unit_price=food.price,
            subtotal=subtotal
        ))
            
    if total <= 0 or not math.isfinite(total):
        db.session.rollback()
        flash('Tổng giá trị đơn hàng không hợp lệ!', 'danger')
        return redirect(request.referrer or url_for('admin_orders'))
        
    new_order.total_price = total
    db.session.commit()
    
    flash(f'Tạo thành công đơn hàng #{order_code} ({format_currency(total)})! Đồ thị và số liệu đã tự động cập nhật.', 'success')
    return redirect(request.referrer or url_for('admin_orders'))

@app.route('/admin/orders/clear-all', methods=['POST'])
def admin_clear_all_orders():
    """Xóa toàn bộ đơn hàng trong CSDL để người dùng tự nhập từ đầu nếu muốn"""
    OrderItem.query.delete()
    Order.query.delete()
    db.session.commit()
    flash('Đã xóa toàn bộ đơn hàng! Hệ thống sạch 100% để bạn tự nhập đơn mới.', 'info')
    return redirect(request.referrer or url_for('admin_orders'))

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    """Cập nhật trạng thái đơn hàng (Đồ thị tự động cập nhật theo)"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    valid_statuses = ['pending', 'confirmed', 'cooking', 'delivering', 'completed', 'cancelled']
    
    if new_status in valid_statuses:
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Đã cập nhật trạng thái đơn #{order.order_code} thành: {new_status.upper()} (Đồ thị đã tự động cập nhật!)', 'success')
    else:
        flash('Trạng thái không hợp lệ!', 'danger')
        
    return redirect(request.referrer or url_for('admin_orders'))

@app.route('/admin/menu')
def admin_menu():
    """Trang quản lý thực đơn (CRUD món ăn)"""
    foods = FoodItem.query.order_by(FoodItem.category_id, FoodItem.id.desc()).all()
    categories = Category.query.all()
    return render_template('admin/menu.html', foods=foods, categories=categories)

@app.route('/admin/menu/add', methods=['POST'])
def admin_add_food():
    """Thêm món ăn mới vào thực đơn"""
    name = request.form.get('name', '').strip()
    try:
        price = float(request.form.get('price', ''))
        category_id = int(request.form.get('category_id', ''))
    except (ValueError, TypeError):
        flash('Giá bán hoặc danh mục không hợp lệ!', 'danger')
        return redirect(url_for('admin_menu'))

    description = request.form.get('description', '')
    image_url = request.form.get('image_url', '').strip()

    if not name or len(name) > 150 or not math.isfinite(price) or price <= 0:
        flash('Tên món hoặc giá bán không hợp lệ!', 'danger')
        return redirect(url_for('admin_menu'))
    if len(description) > 5000 or len(image_url) > 300:
        flash('Mô tả hoặc đường dẫn ảnh quá dài!', 'danger')
        return redirect(url_for('admin_menu'))
    category = Category.query.filter_by(id=category_id).first()
    if not category:
        flash('Danh mục không tồn tại!', 'danger')
        return redirect(url_for('admin_menu'))

    if image_url:
        if urlparse(image_url).scheme not in {'http', 'https'}:
            flash('Đường dẫn ảnh phải sử dụng HTTP hoặc HTTPS!', 'danger')
            return redirect(url_for('admin_menu'))
    
    if not image_url:
        image_url = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=80"
        
    new_food = FoodItem(
        name=name,
        price=price,
        category_id=category_id,
        description=description,
        image_url=image_url,
        is_available=True
    )
    db.session.add(new_food)
    db.session.commit()
    flash(f'Đã thêm món "{name}" vào thực đơn!', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/<int:food_id>/toggle', methods=['POST'])
def admin_toggle_food(food_id):
    """Bật/tắt trạng thái còn món hay hết món"""
    food = FoodItem.query.get_or_404(food_id)
    food.is_available = not food.is_available
    db.session.commit()
    status_str = "Còn hàng" if food.is_available else "Hết hàng"
    flash(f'Món "{food.name}" hiện đang ở trạng thái: {status_str}', 'info')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/<int:food_id>/delete', methods=['POST'])
def admin_delete_food(food_id):
    """Xóa món ăn"""
    food = FoodItem.query.get_or_404(food_id)
    db.session.delete(food)
    db.session.commit()
    flash(f'Đã xóa món "{food.name}" khỏi thực đơn!', 'warning')
    return redirect(url_for('admin_menu'))

@app.route('/admin/analytics')
def admin_analytics():
    """
    Trang Báo cáo & Phân tích chuyên sâu (BẮT BUỘC YÊU CẦU ĐỒ THỊ)
    Đồ thị Matplotlib, Pandas và Numpy TỰ ĐỘNG CẬP NHẬT theo các đơn hàng được nhập mới
    """
    charts = analytics.generate_all_charts()
    return render_template('admin/analytics.html', charts=charts)

@app.route('/api/admin/analytics/data')
def api_admin_analytics_data():
    """REST API trả về dữ liệu số liệu thô từ Pandas/Numpy"""
    data = analytics.get_analytics_data()
    return jsonify({
        'success': True,
        'kpis': data['kpis'],
        'top_foods': data['top_foods'].to_dict(orient='records'),
        'cat_share': data['cat_share'].to_dict(orient='records'),
        'hourly_dist': data['hourly_dist'].to_dict(orient='records')
    })

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true')
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    print("=" * 60)
    print(" 🍔 WEBSITE ĐẶT MÓN ĂN VÀ QUẢN LÝ ĐƠN HÀNG TRỰC TUYẾN 🍜")
    print(" - Chế độ: Tự nhập đơn hàng & Đồ thị tự động cập nhật thời gian thực")
    print(" - Khách hàng đặt món: http://127.0.0.1:5000/")
    print(" - Quản trị nhập đơn & Đồ thị: http://127.0.0.1:5000/admin")
    print("=" * 60)
    app.run(debug=debug, host=host, port=port)
