"""
数据加载层 — 封装所有数据源的取数逻辑
每个函数自己决定连哪个库、写什么 SQL，外部调用方不关心
"""
import pandas as pd
from config import get_kingdee_engine, get_ufida_engine

# ═══════════════════════════════════════════════════════
# 金蝶 MySQL — 产品、客户、订单、库存
# ═══════════════════════════════════════════════════════

def load_products():
    """产品表（带品类、成本价）"""
    engine = get_kingdee_engine()
    df = pd.read_sql_query("""
        SELECT p.product_id, p.name AS product_name,
               COALESCE(pc.name, '未分类') AS category,
               CAST(p.price AS DECIMAL(10,2)) AS unit_price,
               CAST(COALESCE(MIN(i.purchase_price), p.price*0.4) AS DECIMAL(10,2)) AS cost_price,
               p.status, p.quantity AS stock
        FROM products p
        LEFT JOIN product_category_relationship pcr ON p.product_id = pcr.product_id
        LEFT JOIN product_categories pc ON pcr.category_id = pc.category_id
        LEFT JOIN inventory i ON p.product_id = i.product_id
        GROUP BY p.product_id, p.name, pc.name, p.price, p.status, p.quantity
    """, engine)
    df["gross_margin_pct"] = ((df["unit_price"]-df["cost_price"])/df["unit_price"]*100).round(1)
    return df

def load_customers():
    """客户表"""
    engine = get_kingdee_engine()
    return pd.read_sql_query("""
        SELECT user_id AS customer_id, username AS customer_name
        FROM users WHERE status='active'
    """, engine)

def load_orders():
    """销售事实表（订单+明细+客户+产品）"""
    engine = get_kingdee_engine()
    df = pd.read_sql_query("""
        SELECT oi.order_item_id, o.order_id,
               o.created_at AS order_date,
               u.username AS customer_name,
               p.name AS product_name,
               oi.quantity,
               CAST(p.price AS DECIMAL(10,2)) AS unit_price,
               CAST(oi.quantity * p.price AS DECIMAL(10,2)) AS amount,
               o.status
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN users u ON o.user_id = u.user_id
        JOIN products p ON oi.product_id = p.product_id
        ORDER BY o.created_at
    """, engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["order_month"] = df["order_date"].dt.to_period("M")
    return df

def load_inventory():
    """库存表"""
    engine = get_kingdee_engine()
    df = pd.read_sql_query("""
        SELECT i.inventory_id, i.product_id, p.name AS product_name,
               i.quantity AS current_stock, 50 AS safety_stock,
               CAST(i.purchase_price AS DECIMAL(10,2)) AS purchase_price,
               i.supplier_info, i.created_at AS check_date
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
    """, engine)
    df.loc[df["current_stock"] < 0, "current_stock"] = 0
    return df

# ═══════════════════════════════════════════════════════
# 用友 SQL Server — 回款、财务
# ═══════════════════════════════════════════════════════
# Excel 文件 — 销售内勤手工汇总的经销商订单
# ═══════════════════════════════════════════════════════

def load_dealer_orders():
    """经销商订单 — 从销售内勤的手工 Excel 加载，不是数据库"""
    from pathlib import Path
    filepath = Path(__file__).parent / "data" / "dealer_orders.xlsx"
    raw = pd.read_excel(filepath)

    # 列名标准化（跟 MySQL 订单表对齐）
    df = raw.rename(columns={
        "订单号": "order_id", "日期": "date_str", "客户单位": "customer_name",
        "货品名称": "product_name", "数量": "quantity",
        "单价": "unit_price", "金额": "amount",
    })

    # 中文日期 → datetime
    def parse_cn_date(val):
        if pd.isna(val) or str(val).strip() == "":
            return pd.NaT
        return pd.to_datetime(str(val).strip().replace("年","-").replace("月","-").replace("日",""), errors="coerce")

    df["order_date"] = df["date_str"].apply(parse_cn_date)
    df = df[df["order_date"].notna()]
    df = df.drop(columns=["date_str"])

    # 数值列清洗（"待确认" → NaN → 删掉）
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df = df.dropna(subset=["amount", "unit_price", "quantity", "customer_name"])

    # 异常高价剔除
    cap = df["unit_price"].quantile(0.99)
    df = df[df["unit_price"] <= cap]

    df["order_month"] = df["order_date"].dt.to_period("M")
    df["channel"] = "经销商"  # 标记来源
    df["status"] = "completed"
    return df[["order_id","order_date","order_month","customer_name",
               "product_name","quantity","unit_price","amount","channel","status"]]

# ═══════════════════════════════════════════════════════
# 用友 SQL Server — 回款、财务
# ═══════════════════════════════════════════════════════

def load_collections():
    """回款表 — 连的是用友，不是金蝶"""
    engine = get_ufida_engine()
    return pd.read_sql_query("""
        SELECT p.payment_id, p.order_id, u.username AS customer_name,
               CAST(p.amount AS DECIMAL(10,2)) AS receivable,
               CAST(CASE WHEN p.status='completed' THEN p.amount ELSE 0 END AS DECIMAL(10,2)) AS collected,
               CAST(CASE WHEN p.status='completed' THEN 0 ELSE p.amount END AS DECIMAL(10,2)) AS outstanding,
               p.status, p.payment_time AS last_payment_date
        FROM payments p
        LEFT JOIN orders o ON p.order_id = o.order_id
        LEFT JOIN users u ON o.user_id = u.user_id
    """, engine)
