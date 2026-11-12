import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Chế độ headless cho Web Server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from models import db, Order, OrderItem, FoodItem, Category

# Cấu hình thẩm mỹ đồ họa
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#f1f5f9'
plt.rcParams['grid.linestyle'] = '--'

def get_analytics_data():
    """
    Sử dụng PANDAS và NUMPY để trích xuất và tính toán toàn bộ số liệu thống kê từ CSDL.
    Hỗ trợ xử lý hoàn hảo trường hợp chưa có đơn hàng nào hoặc chỉ có 1-2 đơn do người dùng tự nhập.
    """
    empty_kpis = {
        'total_orders': 0,
        'valid_orders_count': 0,
        'cancelled_orders_count': 0,
        'total_revenue': 0.0,
        'mean_order_value': 0.0,
        'median_order_value': 0.0,
        'std_order_value': 0.0,
        'min_order_value': 0.0,
        'max_order_value': 0.0,
        'percentile_25': 0.0,
        'percentile_75': 0.0,
        'percentile_90': 0.0,
    }
    
    empty_hourly = pd.DataFrame({'hour': range(24), 'orders_count': [0]*24})

    orders = Order.query.all()
    if not orders:
        return {
            'df_orders': pd.DataFrame(),
            'df_items': pd.DataFrame(),
            'valid_orders': pd.DataFrame(),
            'kpis': empty_kpis,
            'daily_rev': pd.DataFrame(columns=['date', 'revenue', 'orders_count']),
            'top_foods': pd.DataFrame(columns=['food_name', 'total_qty', 'total_rev']),
            'cat_share': pd.DataFrame(columns=['category_name', 'total_qty', 'total_rev']),
            'hourly_dist': empty_hourly
        }

    # 1. Chuyển đổi dữ liệu Orders sang Pandas DataFrame
    orders_data = [{
        'id': o.id,
        'order_code': o.order_code,
        'total_price': o.total_price,
        'status': o.status,
        'payment_method': o.payment_method,
        'created_at': o.created_at,
        'date': o.created_at.date(),
        'hour': o.created_at.hour
    } for o in orders]
    
    df_orders = pd.DataFrame(orders_data)
    df_orders['created_at'] = pd.to_datetime(df_orders['created_at'])
    
    # 2. Chuyển đổi dữ liệu Order Items sang Pandas DataFrame
    items = db.session.query(
        OrderItem.id,
        OrderItem.order_id,
        OrderItem.food_name,
        OrderItem.quantity,
        OrderItem.unit_price,
        OrderItem.subtotal,
        FoodItem.category_id,
        Category.name.label('category_name')
    ).outerjoin(FoodItem, OrderItem.food_item_id == FoodItem.id)\
     .outerjoin(Category, FoodItem.category_id == Category.id).all()
     
    items_data = [{
        'id': it.id,
        'order_id': it.order_id,
        'food_name': it.food_name,
        'quantity': it.quantity,
        'unit_price': it.unit_price,
        'subtotal': it.subtotal,
        'category_name': it.category_name or 'Khác'
    } for it in items]
    
    df_items = pd.DataFrame(items_data) if items_data else pd.DataFrame(
        columns=['id', 'order_id', 'food_name', 'quantity', 'unit_price', 'subtotal', 'category_name']
    )
    
    # Chỉ tính doanh thu các đơn hợp lệ (không bị hủy)
    valid_orders = df_orders[df_orders['status'] != 'cancelled']
    
    if not valid_orders.empty:
        revenue_array = valid_orders['total_price'].to_numpy(dtype=float)
        kpis = {
            'total_orders': int(len(df_orders)),
            'valid_orders_count': int(len(valid_orders)),
            'cancelled_orders_count': int(len(df_orders[df_orders['status'] == 'cancelled'])),
            'total_revenue': float(np.sum(revenue_array)),
            'mean_order_value': float(np.mean(revenue_array)),
            'median_order_value': float(np.median(revenue_array)),
            'std_order_value': float(np.std(revenue_array)),
            'min_order_value': float(np.min(revenue_array)),
            'max_order_value': float(np.max(revenue_array)),
            'percentile_25': float(np.percentile(revenue_array, 25)),
            'percentile_75': float(np.percentile(revenue_array, 75)),
            'percentile_90': float(np.percentile(revenue_array, 90)),
        }
    else:
        kpis = empty_kpis
        kpis['total_orders'] = int(len(df_orders))
        kpis['cancelled_orders_count'] = int(len(df_orders))

    # === TỔNG HỢP PANDAS ===
    # Doanh thu theo ngày
    if not valid_orders.empty:
        daily_rev = valid_orders.groupby('date').agg(
            revenue=('total_price', 'sum'),
            orders_count=('id', 'count')
        ).reset_index().sort_values('date')
    else:
        daily_rev = pd.DataFrame(columns=['date', 'revenue', 'orders_count'])
        
    # Top món ăn
    if not df_items.empty:
        top_foods = df_items.groupby('food_name').agg(
            total_qty=('quantity', 'sum'),
            total_rev=('subtotal', 'sum')
        ).reset_index().sort_values('total_qty', ascending=False)
    else:
        top_foods = pd.DataFrame(columns=['food_name', 'total_qty', 'total_rev'])
        
    # Phân bổ theo danh mục
    if not df_items.empty:
        cat_share = df_items.groupby('category_name').agg(
            total_qty=('quantity', 'sum'),
            total_rev=('subtotal', 'sum')
        ).reset_index().sort_values('total_rev', ascending=False)
    else:
        cat_share = pd.DataFrame(columns=['category_name', 'total_qty', 'total_rev'])
        
    # Khung giờ đặt
    hourly_dist = df_orders.groupby('hour').agg(
        orders_count=('id', 'count')
    ).reindex(range(24), fill_value=0).reset_index()

    return {
        'df_orders': df_orders,
        'df_items': df_items,
        'valid_orders': valid_orders,
        'kpis': kpis,
        'daily_rev': daily_rev,
        'top_foods': top_foods,
        'cat_share': cat_share,
        'hourly_dist': hourly_dist
    }

def fig_to_base64(fig):
    """Chuyển đổi Figure của Matplotlib thành chuỗi Base64 để nhúng vào thẻ <img> HTML"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=130, facecolor='#ffffff')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{img_b64}"

def draw_empty_placeholder(ax, message="Chưa có dữ liệu đơn hàng"):
    """Vẽ thông báo trực quan khi chưa có dữ liệu"""
    ax.text(0.5, 0.55, message, ha='center', va='center', fontsize=12, fontweight='bold', color='#64748b')
    ax.text(0.5, 0.42, 'Hãy tạo đơn hàng mới trên web hoặc nhập đơn thủ công để đồ thị tự động vẽ!', 
            ha='center', va='center', fontsize=9.5, color='#94a3b8')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

def generate_revenue_trend_chart(daily_rev):
    """Biểu đồ 1: Xu hướng Doanh thu theo Ngày + Hồi quy tuyến tính (Numpy Polyfit)"""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    
    if daily_rev.empty:
        draw_empty_placeholder(ax, "Chưa có đơn hàng hợp lệ nào")
        ax.set_title('Xu Hướng Doanh Thu Theo Thời Gian (Tự Động Cập Nhật)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
        return fig_to_base64(fig)
        
    dates = pd.to_datetime(daily_rev['date'])
    revenues_m = daily_rev['revenue'] / 1000.0  # Đổi sang ngàn VNĐ
    
    # Nếu chỉ có 1 ngày duy nhất
    if len(dates) == 1:
        ax.bar(dates, revenues_m, color='#ea580c', width=0.4, label='Doanh thu (Nghìn VNĐ)')
        ax.annotate(f"{revenues_m.iloc[0]:,.0f}k",
                    xy=(dates.iloc[0], revenues_m.iloc[0]),
                    xytext=(0, 6), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color='#ea580c')
    else:
        # Nhiều ngày: vẽ đường & diện tích
        ax.fill_between(dates, revenues_m, color='#f97316', alpha=0.15)
        ax.plot(dates, revenues_m, color='#ea580c', marker='o', linewidth=2.5, markersize=5, label='Doanh thu (Nghìn VNĐ)')
        
        # Tính đường xu hướng tuyến tính bằng NUMPY polyfit (khi có từ 2 ngày trở lên)
        x_numeric = np.arange(len(dates))
        poly_coeff = np.polyfit(x_numeric, revenues_m, deg=1)
        poly_fn = np.poly1d(poly_coeff)
        ax.plot(dates, poly_fn(x_numeric), color='#0284c7', linestyle='--', linewidth=2, label='Đường xu hướng (Numpy Polyfit)')
    
    ax.set_title('Xu Hướng Doanh Thu Theo Thời Gian (Tự Động Cập Nhật)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
    ax.set_ylabel('Doanh thu (1.000 VNĐ)', fontsize=10, color='#475569')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper left', frameon=True, facecolor='#ffffff', edgecolor='#e2e8f0')
    
    plt.xticks(rotation=25)
    plt.tight_layout()
    return fig_to_base64(fig)

def generate_top_foods_chart(top_foods):
    """Biểu đồ 2: Top món ăn bán chạy nhất (Horizontal Bar Chart)"""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    
    if top_foods.empty:
        draw_empty_placeholder(ax, "Chưa có món ăn nào được đặt")
        ax.set_title('Top Món Ăn Bán Chạy Nhất (Tự Động Cập Nhật)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
        return fig_to_base64(fig)
        
    top_7 = top_foods.head(7).iloc[::-1]
    names = [name[:22] + '...' if len(name) > 25 else name for name in top_7['food_name']]
    qtys = top_7['total_qty'].values
    
    colors = plt.cm.Oranges(np.linspace(0.4, 0.85, max(1, len(names))))
    bars = ax.barh(names, qtys, color=colors, height=0.6, edgecolor='#ea580c', linewidth=1)
    
    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{int(width)} suất',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(6, 0), textcoords="offset points",
                    ha='left', va='center', fontsize=9, fontweight='bold', color='#1e293b')
                    
    ax.set_title('Top Món Ăn Bán Chạy Nhất (Số lượng suất đặt)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
    ax.set_xlabel('Số lượng đã bán', fontsize=10, color='#475569')
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    
    if len(qtys) > 0 and max(qtys) > 0:
        ax.set_xlim(0, max(qtys) * 1.3)
        
    plt.tight_layout()
    return fig_to_base64(fig)

def generate_category_share_chart(cat_share):
    """Biểu đồ 3: Tỷ trọng doanh thu theo Danh mục món ăn (Donut Chart)"""
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    
    if cat_share.empty or cat_share['total_rev'].sum() == 0:
        draw_empty_placeholder(ax, "Chưa có doanh thu theo danh mục")
        ax.set_title('Cơ Cấu Doanh Thu Theo Danh Mục', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
        return fig_to_base64(fig)
        
    labels = cat_share['category_name'].tolist()
    revenues = cat_share['total_rev'].tolist()
    colors = ['#f97316', '#3b82f6', '#10b981', '#a855f7', '#f43f5e', '#eab308']
    
    wedges, texts, autotexts = ax.pie(
        revenues,
        labels=labels,
        autopct='%1.1f%%',
        startangle=140,
        pctdistance=0.75,
        colors=colors[:len(labels)],
        wedgeprops=dict(width=0.45, edgecolor='w', linewidth=2)
    )
    
    for autotext in autotexts:
        autotext.set_color('#ffffff')
        autotext.set_weight('bold')
        autotext.set_fontsize(9)
        
    for text in texts:
        text.set_color('#334155')
        text.set_fontsize(9.5)
        
    ax.set_title('Cơ Cấu Doanh Thu Theo Danh Mục', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
    plt.tight_layout()
    return fig_to_base64(fig)

def generate_hourly_orders_chart(hourly_dist):
    """Biểu đồ 4: Phân bố số lượng đơn hàng theo 24 khung giờ"""
    fig, ax = plt.subplots(figsize=(9, 4.2))
    
    hours = hourly_dist['hour'].values
    counts = hourly_dist['orders_count'].values
    
    bar_colors = ['#f97316' if (11 <= h <= 13 or 18 <= h <= 20) else '#94a3b8' for h in hours]
    ax.bar(hours, counts, color=bar_colors, width=0.75, edgecolor='#475569', linewidth=0.5)
    
    ax.set_title('Phân Bố Số Lượng Đơn Đặt Theo 24 Khung Giờ (Cao điểm Trưa & Tối)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
    ax.set_xlabel('Khung giờ trong ngày (0h - 23h)', fontsize=10, color='#475569')
    ax.set_ylabel('Số đơn hàng', fontsize=10, color='#475569')
    ax.set_xticks(range(0, 24))
    ax.set_xticklabels([f'{h}h' for h in range(24)], fontsize=8)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    max_c = max(counts) if len(counts) > 0 else 0
    ax.set_ylim(0, max(5, max_c + 2))
    
    plt.tight_layout()
    return fig_to_base64(fig)

def generate_box_plot_chart(valid_orders):
    """Biểu đồ 5: Phân tích phân vị giá trị đơn hàng (Numpy Percentiles Boxplot)"""
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    
    if valid_orders.empty:
        draw_empty_placeholder(ax, "Chưa có đơn hàng để phân tích phân vị")
        ax.set_title('Phân Phối Giá Trị Đơn Hàng (Boxplot)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
        return fig_to_base64(fig)
        
    revenues_k = (valid_orders['total_price'] / 1000.0).values
    
    bp = ax.boxplot(revenues_k, patch_artist=True, vert=True,
                    boxprops=dict(facecolor='#fed7aa', color='#ea580c', linewidth=1.5),
                    whiskerprops=dict(color='#ea580c', linewidth=1.5),
                    capprops=dict(color='#ea580c', linewidth=1.5),
                    medianprops=dict(color='#c2410c', linewidth=2.5),
                    flierprops=dict(marker='o', color='#ea580c', alpha=0.6))
                    
    ax.set_title('Phân Phối Giá Trị Đơn Hàng (Boxplot Phân Vị)', fontsize=13, fontweight='bold', pad=15, color='#1e293b')
    ax.set_ylabel('Giá trị đơn (Nghìn VNĐ)', fontsize=10, color='#475569')
    ax.set_xticklabels(['Đơn hàng'])
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    return fig_to_base64(fig)

def generate_all_charts():
    """Tạo toàn bộ biểu đồ để trả về cho GUI Admin Dashboard"""
    data = get_analytics_data()
    charts = {
        'revenue_trend': generate_revenue_trend_chart(data['daily_rev']),
        'top_foods': generate_top_foods_chart(data['top_foods']),
        'category_share': generate_category_share_chart(data['cat_share']),
        'hourly_orders': generate_hourly_orders_chart(data['hourly_dist']),
        'boxplot': generate_box_plot_chart(data['valid_orders']),
        'kpis': data['kpis']
    }
    return charts
