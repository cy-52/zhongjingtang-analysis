-- CI 测试用数据库结构（简化版，去掉了外键约束避免导入顺序问题）
-- 真实项目会用 Alembic/Flyway 管理这类文件

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('available','unavailable') DEFAULT 'available',
    quantity INT DEFAULT 0,
    review_status INT DEFAULT 0
);

CREATE TABLE product_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE product_category_relationship (
    product_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (product_id, category_id)
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active','inactive','banned') DEFAULT 'active',
    balance DECIMAL(10,2) DEFAULT 0.00,
    purchase_count INT DEFAULT 0
);

CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending','completed','failed') DEFAULT 'pending'
);

CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    purchase_price DECIMAL(10,2) NOT NULL,
    supplier_info VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payment_channels (
    channel_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    channel_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending','completed','failed') DEFAULT 'pending',
    payment_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_id VARCHAR(255) UNIQUE,
    payment_method VARCHAR(100)
);

-- 插入最小测试数据
INSERT INTO product_categories VALUES (1,'艾制品',''),(2,'贴敷类',''),(3,'理疗仪','');
INSERT INTO products VALUES (1,'蕲艾条·三年陈',28.00,'',NOW(),'available',100,0),(2,'艾灸贴·自发热型',18.00,'',NOW(),'available',50,0),(3,'电子灸疗仪·台式',680.00,'',NOW(),'available',10,0);
INSERT INTO product_category_relationship VALUES (1,1),(2,1),(3,3);
INSERT INTO users VALUES (1,'test@test.com','123456','测试用户',NOW(),'active',0,0);
INSERT INTO payment_channels VALUES (1,'微信支付');
INSERT INTO orders VALUES (1,1,180.00,0,NOW(),'completed');
INSERT INTO order_items VALUES (1,1,1,5,NOW()),(2,1,2,2,NOW());
INSERT INTO inventory VALUES (1,1,100,12.00,'测试供应商',NOW()),(2,2,50,5.00,'',NOW());
INSERT INTO payments VALUES (1,1,1,180.00,'pending',NOW(),'TXN001','微信');
