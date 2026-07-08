"""
数据加载层 — 所有数据源的取数、清洗、标准化。

数据来源：
  金蝶 MySQL   — 产品档案、客户档案、库存（仓库主管 + 销售经理维护）
  电商 MySQL   — 小程序商城订单、用户（消费者端）
  销售内勤 Excel — 经销商手工订单（金蝶和电商都不管的渠道）
  用友 MySQL   — 回款记录（财务出纳维护）

每个函数返回标准化的 DataFrame，列名、数据类型统一，调用方不需要关心数据来源。
新增数据源只需在这里加一个函数，不碰上层分析代码。
"""
import pandas as pd
from pathlib import Path
from config import get_kingdee_engine, get_ufida_engine


# ═══════════════════════════════════════════════════════
# 来源一：金蝶 MySQL（产品、客户、订单、库存）
# 找仓库主管 + 销售经理要只读账号
# ═══════════════════════════════════════════════════════

def load_products():
    """
    产品档案 — 金蝶·基础资料模块
    来源：仓库主管每月从金蝶导出的商品档案
    清洗：缺成本价 → 同品类中位数填充；衍生毛利率字段
    返回 36 种艾草产品（product_id / product_name / category / unit_price / cost_price / gross_margin_pct / stock）
    """
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
    df["gross_margin_pct"] = ((df["unit_price"] - df["cost_price"]) / df["unit_price"] * 100).round(1)
    return df


def load_customers():
    """
    客户档案 — 金蝶·客户管理模块
    来源：销售经理每月从金蝶导出（药店/医院/经销商/个人）
    只取状态为 active 的活跃客户
    """
    engine = get_kingdee_engine()
    return pd.read_sql_query("""
        SELECT user_id AS customer_id, username AS customer_name
        FROM users WHERE status = 'active'
    """, engine)


def load_orders():
    """
    电商销售事实表 — 小程序商城 MySQL（mugwort 库）
    来源：消费者在小程序自行下单，系统自动记录
    清洗：日期转 datetime、金额转 numeric、派生 order_month 用于月度聚合
    返回 (order_item_id / order_id / order_date / customer_name / product_name / quantity / unit_price / amount / status)
    """
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
        JOIN orders o      ON oi.order_id = o.order_id
        JOIN users u       ON o.user_id = u.user_id
        JOIN products p    ON oi.product_id = p.product_id
        ORDER BY o.created_at
    """, engine)
    df["order_date"]  = pd.to_datetime(df["order_date"])
    df["order_month"] = df["order_date"].dt.to_period("M")
    return df


def load_inventory():
    """
    库存表 — 金蝶·库存管理模块
    来源：仓库主管每月末导出的盘点快照
    清洗：负库存 → 设为 0（系统 bug，实际不存在）；补安全库存基准值
    """
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
# 来源二：销售内勤 Excel（经销商手工订单）
# 找销售内勤小陈要，文件在 data/dealer_orders.xlsx
# ═══════════════════════════════════════════════════════

def load_dealer_orders():
    """
    经销商销售订单 — 销售内勤手工录入的 Excel
    来源：经销商通过微信/电话下单 → 销售内勤在 Excel 里手写记录
    特殊处理：
      - 列名中文 → 英文对齐 MySQL 订单表
      - 日期中文格式 "2024年3月15日" → datetime
      - 数值列混入 "待确认" → 转为 NaN 后剔除
      - 单价分位数法去极端异常值（>99 分位）
    返回与 load_orders 相同的列结构，额外带 channel='经销商' 标签
    """
    filepath = Path(__file__).parent / "data" / "dealer_orders.xlsx"
    raw = pd.read_excel(filepath)

    df = raw.rename(columns={
        "订单号": "order_id", "日期": "date_str", "客户单位": "customer_name",
        "货品名称": "product_name", "数量": "quantity",
        "单价": "unit_price", "金额": "amount",
    })

    # 中文日期 → datetime（"2024年3月15日" → 2024-03-15）
    def parse_cn_date(val):
        if pd.isna(val) or str(val).strip() == "":
            return pd.NaT
        s = str(val).strip().replace("年", "-").replace("月", "-").replace("日", "")
        return pd.to_datetime(s, errors="coerce")

    df["order_date"] = df["date_str"].apply(parse_cn_date)
    df = df[df["order_date"].notna()]
    df = df.drop(columns=["date_str"])

    # 数值清洗（"待确认" 不能当金额用）
    df["amount"]     = pd.to_numeric(df["amount"],     errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce")
    df = df.dropna(subset=["amount", "unit_price", "quantity", "customer_name"])

    # 单价异常（录入错误，如多加了一个 9）
    cap = df["unit_price"].quantile(0.99)
    df = df[df["unit_price"] <= cap]

    df["order_month"] = df["order_date"].dt.to_period("M")
    df["channel"] = "经销商"
    df["status"]  = "completed"
    return df[["order_id", "order_date", "order_month", "customer_name",
               "product_name", "quantity", "unit_price", "amount", "channel", "status"]]


# ═══════════════════════════════════════════════════════
# 来源三：用友 MySQL（回款记录）
# 找财务出纳王姐要只读账号
# ═══════════════════════════════════════════════════════

def load_collections():
    """
    回款记录 — 用友·应收款管理模块
    来源：财务出纳每月导出的回款明细
    注意：部分 payment 关联的 order 已被删除（LEFT JOIN 而非 JOIN 的原因）
    派生字段：collected 为实际回款额，outstanding 为未回款余额
    """
    engine = get_ufida_engine()
    return pd.read_sql_query("""
        SELECT p.payment_id, p.order_id, u.username AS customer_name,
               CAST(p.amount AS DECIMAL(10,2)) AS receivable,
               CAST(CASE WHEN p.status = 'completed'
                    THEN p.amount ELSE 0 END AS DECIMAL(10,2)) AS collected,
               CAST(CASE WHEN p.status = 'completed'
                    THEN 0 ELSE p.amount END AS DECIMAL(10,2)) AS outstanding,
               p.status, p.payment_time AS last_payment_date
        FROM payments p
        LEFT JOIN orders o ON p.order_id = o.order_id
        LEFT JOIN users  u ON o.user_id  = u.user_id
    """, engine)
