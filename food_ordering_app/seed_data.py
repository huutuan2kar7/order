from models import db, Category, FoodItem

INITIAL_CATEGORIES = [
    {"name": "Cơm & Món Mặn", "slug": "com-mon-man", "icon": "fa-bowl-rice"},
    {"name": "Phở & Bún Mì", "slug": "pho-bun-mi", "icon": "fa-bowl-food"},
    {"name": "Ăn Vặt & Bánh", "slug": "an-vat-banh", "icon": "fa-burger"},
    {"name": "Trà Sữa & Đồ Uống", "slug": "tra-sua-do-uong", "icon": "fa-mug-hot"},
    {"name": "Tráng Miệng", "slug": "trang-mieng", "icon": "fa-ice-cream"},
]

INITIAL_FOODS = [
    # Cơm & Món Mặn
    {
        "name": "Cơm Tấm Sườn Bì Chả Đặc Biệt",
        "category_slug": "com-mon-man",
        "price": 55000,
        "description": "Cơm tấm hạt thơm dẻo, sườn nướng mật ong đậm đà, bì thơm và chả trứng mềm ngậy cùng mỡ hành tóp mỡ giòn rụm.",
        "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=80",
        "rating": 4.9
    },
    {
        "name": "Cơm Gà Xối Mỡ Da Giòn",
        "category_slug": "com-mon-man",
        "price": 50000,
        "description": "Cơm đảo hạt vàng óng ánh, đùi gà góc tư chiên xối mỡ lớp da giòn rụm, thịt bên trong mềm ngọt mọng nước.",
        "image_url": "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?w=500&auto=format&fit=crop&q=80",
        "rating": 4.8
    },
    {
        "name": "Cơm Bò Xào Lúc Lắc",
        "category_slug": "com-mon-man",
        "price": 65000,
        "description": "Thịt thăn bò mềm xào áp chảo với ớt chuông, hành tây và sốt tiêu đen sánh quyện thơm lừng.",
        "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=500&auto=format&fit=crop&q=80",
        "rating": 4.7
    },
    
    # Phở & Bún Mì
    {
        "name": "Phở Bò Tái Nạm Gầu Bắp",
        "category_slug": "pho-bun-mi",
        "price": 60000,
        "description": "Nước dùng ninh từ xương ống bò trong 18 tiếng ngọt thanh thơm thảo quả, thịt bò tươi mềm, bánh phở dai ngon.",
        "image_url": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=500&auto=format&fit=crop&q=80",
        "rating": 5.0
    },
    {
        "name": "Bún Bò Huế Thập Cẩm Chả Cua",
        "category_slug": "pho-bun-mi",
        "price": 55000,
        "description": "Nước dùng cay nồng hương sả mắm ruốc chuẩn vị cố đô, ăn kèm bắp bò, giò heo, tiết và chả cua hấp dẫn.",
        "image_url": "https://images.unsplash.com/photo-1594998893017-36147cbcae05?w=500&auto=format&fit=crop&q=80",
        "rating": 4.9
    },
    {
        "name": "Bún Chả Hà Nội Nướng Than Hoa",
        "category_slug": "pho-bun-mi",
        "price": 50000,
        "description": "Chả miếng và chả viên nướng xém cạnh trên than hoa, nước mắm dưa góp chua ngọt chuẩn gốc Hà Thành.",
        "image_url": "https://images.unsplash.com/photo-1555126634-323283e090fa?w=500&auto=format&fit=crop&q=80",
        "rating": 4.8
    },
    
    # Ăn Vặt & Bánh
    {
        "name": "Bánh Mì Kẹp Thịt Nướng Pâté",
        "category_slug": "an-vat-banh",
        "price": 30000,
        "description": "Vỏ bánh mì giòn tan nóng hổi, nhân thịt nướng thơm lừng, pa-tê gan béo bùi và đồ chua ngò gai thanh mát.",
        "image_url": "https://images.unsplash.com/photo-1626804475297-41608ea09aeb?w=500&auto=format&fit=crop&q=80",
        "rating": 4.7
    },
    {
        "name": "Gà Rán Giòn Sốt Cay Hàn Quốc",
        "category_slug": "an-vat-banh",
        "price": 69000,
        "description": "Gà rút xương chiên 2 lần giòn rụm áo đẫm lớp sốt Gochujang ngọt cay phủ mè trắng rang thơm.",
        "image_url": "https://images.unsplash.com/photo-1562967914-608f82629710?w=500&auto=format&fit=crop&q=80",
        "rating": 4.8
    },
    {
        "name": "Khoai Tây Chiên Lắc Phô Mai",
        "category_slug": "an-vat-banh",
        "price": 35000,
        "description": "Khoai tây cọng giòn rụm vàng ươm, lắc đều cùng bột phô mai béo ngậy mằn mặn thơm nức.",
        "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=500&auto=format&fit=crop&q=80",
        "rating": 4.6
    },
    
    # Trà Sữa & Đồ Uống
    {
        "name": "Trà Sữa Trân Châu Đường Đen Hoàng Gia",
        "category_slug": "tra-sua-do-uong",
        "price": 39000,
        "description": "Trà sữa đậm vị hồng trà Ceylon kết hợp trân châu thủ công nấu đường mía thơm lừng dai dẻo.",
        "image_url": "https://images.unsplash.com/photo-1558857563-b37cfbbfb41a?w=500&auto=format&fit=crop&q=80",
        "rating": 4.9
    },
    {
        "name": "Trà Đào Cam Sả Tươi Mát",
        "category_slug": "tra-sua-do-uong",
        "price": 35000,
        "description": "Vị thanh ngọt của đào hòa quyện cùng vị chua nhẹ của cam vàng tươi và hương thơm the mát nồng ấm từ sả.",
        "image_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=500&auto=format&fit=crop&q=80",
        "rating": 4.8
    },
    {
        "name": "Cà Phê Muối Kem Béo Huế",
        "category_slug": "tra-sua-do-uong",
        "price": 32000,
        "description": "Cà phê pha phin truyền thống thơm đắng kết hợp lớp kem sữa mặn béo ngậy tạo nên hương vị bùng nổ.",
        "image_url": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500&auto=format&fit=crop&q=80",
        "rating": 4.9
    },
    
    # Tráng Miệng
    {
        "name": "Chè Khúc Bạch Hạnh Nhân Thanh Mát",
        "category_slug": "trang-mieng",
        "price": 35000,
        "description": "Những viên khúc bạch mềm tan béo ngậy vị sữa tươi, ăn cùng nhãn tươi giòn, nước đường phèn và hạnh nhân lát rang vàng.",
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop&q=80",
        "rating": 4.8
    },
    {
        "name": "Caramel Rau Câu Trứng Sữa",
        "category_slug": "trang-mieng",
        "price": 25000,
        "description": "Bánh flan mềm mịn không rỗ, thơm béo hương trứng sữa kết hợp sốt caramel đắng nhẹ và cà phê đá bào.",
        "image_url": "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=500&auto=format&fit=crop&q=80",
        "rating": 4.7
    }
]

def init_seed_data():
    """Khởi tạo danh mục và món ăn ban đầu (KHÔNG tự động tạo sẵn đơn hàng)"""
    if Category.query.first():
        return  # Đã có thực đơn
        
    print("[Seed] Khởi tạo danh mục & thực đơn món ăn...")
    cat_map = {}
    for cat_data in INITIAL_CATEGORIES:
        cat = Category(name=cat_data["name"], slug=cat_data["slug"], icon=cat_data["icon"])
        db.session.add(cat)
        cat_map[cat_data["slug"]] = cat
        
    db.session.flush()
    
    for food_data in INITIAL_FOODS:
        cat = cat_map[food_data["category_slug"]]
        f = FoodItem(
            name=food_data["name"],
            category_id=cat.id,
            price=food_data["price"],
            description=food_data["description"],
            image_url=food_data["image_url"],
            rating=food_data["rating"],
            is_available=True
        )
        db.session.add(f)
        
    db.session.commit()
    print("[Seed] Khởi tạo thực đơn thành công! (Số lượng đơn hàng ban đầu: 0)")
