import os
import time
import random
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from sqlalchemy.exc import OperationalError

from config import Config
from models import db, Category, FoodItem, Order, OrderItem
from seed_data import init_seed_data
import analytics

app = Flask(__name__)
app.config.from_object(Config)

# Khởi tạo CSDL với cơ chế Fallback: MySQL -> SQLite
try:
    db.init_app(app)
    with app.app_context():
        db.create_all()
        init_seed_data()
        print(f"[Database] Đang kết nối tới: {app.config['SQLALCHEMY_DATABASE_URI']}")
except OperationalError as e:
    print(f"[Database Warning] Không thể kết nối tới MySQL ({e}). Tự động chuyển sang SQLite nội bộ...")
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLITE_URI
    db.init_app(app)
    with app.app_context():
        db.create_all()
        init_seed_data()
        print(f"[Database] Đã chuyển đổi thành công sang SQLite: {Config.SQLITE_URI}")

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
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    return render_template('order_success.html', order=order)

@app.route('/track', methods=['GET', 'POST'])
def track_order():
    """Tra cứu đơn hàng qua Mã đơn hoặc Số điện thoại"""
    order = None
    searched = False
    query = request.args.get('code', '').strip()
    
    if query:
        searched = True
        order = Order.query.filter(
            (Order.order_code == query) | (Order.customer_phone == query)
        ).order_by(Order.created_at.desc()).first()
        
    return render_template('track_order.html', order=order, query=query, searched=searched)

# ==============================================================================
# 2. REST API (TRUYỀN THÔNG MẠNG / NETWORK COMMUNICATION)
# ==============================================================================

@app.route('/api/order/create', methods=['POST'])
def api_create_order():
    """API Tạo đơn hàng mới từ Web Client qua giao thức HTTP POST JSON"""
    data = request.get_json()
    if not data or not data.get('items'):
        return jsonify({'success': False, 'message': 'Giỏ hàng trống hoặc dữ liệu không hợp lệ!'}), 400
        
    customer_name = data.get('customer_name', '').strip()
    customer_phone = data.get('customer_phone', '').strip()
    customer_address = data.get('customer_address', '').strip()
    notes = data.get('notes', '').strip()
    payment_method = data.get('payment_method', 'COD')
    items = data.get('items', [])
    
    if not customer_name or not customer_phone or not customer_address:
        return jsonify({'success': False, 'message': 'Vui lòng điền đầy đủ Họ tên, SĐT và Địa chỉ giao hàng!'}), 400
        
    order_code = f"ORD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
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
    for item in items:
        food_id = item.get('id')
        qty = int(item.get('quantity', 1))
        food = FoodItem.query.get(food_id)
        if food:
            subtotal = food.price * qty
            total += subtotal
            order_item = OrderItem(
                order_id=new_order.id,
                food_item_id=food.id,
                food_name=food.name,
                quantity=qty,
                unit_price=food.price,
                subtotal=subtotal
            )
            db.session.add(order_item)
            
    new_order.total_price = total
    db.session.commit()
    
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
    return jsonify({'success': True, 'order': order.to_dict()})

@app.route('/api/orders/live-stream')
def api_orders_live_stream():
    """Server-Sent Events (SSE) phát thông báo đơn hàng mới qua mạng theo thời gian thực"""
    def event_stream():
        last_id = 0
        while True:
            with app.app_context():
                latest_order = Order.query.order_by(Order.id.desc()).first()
                if latest_order and latest_order.id != last_id:
                    last_id = latest_order.id
                    payload = json.dumps({
                        'event': 'new_order',
                        'order': latest_order.to_dict()
                    })
                    yield f"data: {payload}\n\n"
            time.sleep(3)
            
    return Response(event_stream(), mimetype="text/event-stream")

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
    cooking_count = Order.query.filter_by(status='cooking').count()
    delivering_count = Order.query.filter_by(status='delivering').count()
    
    trend_chart = analytics.generate_revenue_trend_chart(data['daily_rev'])
    foods = FoodItem.query.filter_by(is_available=True).all()
    
    return render_template('admin/dashboard.html',
                           kpis=kpis,
                           recent_orders=recent_orders,
                           pending_count=pending_count,
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
    
    # Lấy danh sách món ăn từ form
    food_ids = request.form.getlist('food_id[]')
    quantities = request.form.getlist('quantity[]')
    
    if not customer_name or not customer_phone or not food_ids:
        flash('Vui lòng nhập tên khách hàng, SĐT và chọn ít nhất 1 món ăn!', 'danger')
        return redirect(request.referrer or url_for('admin_orders'))
        
    # Thời gian tạo đơn (nếu người dùng chọn ngày giờ trong quá khứ/hiện tại)
    if order_date_str:
        try:
            created_at = datetime.strptime(order_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            created_at = datetime.utcnow()
    else:
        created_at = datetime.utcnow()
        
    order_code = f"ORD-{created_at.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
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
    for fid, qty_str in zip(food_ids, quantities):
        if not fid:
            continue
        try:
            qty = max(1, int(qty_str))
            food = FoodItem.query.get(int(fid))
            if food:
                subtotal = food.price * qty
                total += subtotal
                order_item = OrderItem(
                    order_id=new_order.id,
                    food_item_id=food.id,
                    food_name=food.name,
                    quantity=qty,
                    unit_price=food.price,
                    subtotal=subtotal
                )
                db.session.add(order_item)
        except (ValueError, TypeError):
            continue
            
    if total == 0:
        db.session.rollback()
        flash('Lỗi: Tổng giá trị đơn hàng bằng 0 đ! Vui lòng kiểm tra lại món chọn.', 'danger')
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
    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    category_id = int(request.form.get('category_id'))
    description = request.form.get('description', '')
    image_url = request.form.get('image_url', '')
    
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
    print("=" * 60)
    print(" 🍔 WEBSITE ĐẶT MÓN ĂN VÀ QUẢN LÝ ĐƠN HÀNG TRỰC TUYẾN 🍜")
    print(" - Chế độ: Tự nhập đơn hàng & Đồ thị tự động cập nhật thời gian thực")
    print(" - Khách hàng đặt món: http://127.0.0.1:5000/")
    print(" - Quản trị nhập đơn & Đồ thị: http://127.0.0.1:5000/admin")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
