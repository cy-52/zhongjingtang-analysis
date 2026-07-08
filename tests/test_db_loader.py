"""
数据库加载层自动化测试
运行: pytest tests/ -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from db_loader import (load_products, load_customers, load_orders,
                       load_inventory, load_collections, load_dealer_orders)


def test_load_products():
    """产品表: 返回非空 DataFrame，有关键列，有毛利率"""
    df = load_products()
    assert len(df) > 0, "产品表不应为空"
    assert "product_id" in df.columns
    assert "product_name" in df.columns
    assert "category" in df.columns
    assert "cost_price" in df.columns
    assert "unit_price" in df.columns
    assert "gross_margin_pct" in df.columns, "缺少毛利率字段"
    assert (df["gross_margin_pct"] >= 0).all(), "毛利率不应为负"


def test_load_customers():
    """客户表: 返回活跃用户"""
    df = load_customers()
    assert len(df) > 0, "客户表不应为空"
    assert "customer_id" in df.columns
    assert "customer_name" in df.columns
    assert df["customer_name"].notna().all(), "客户名不应为空"


def test_load_orders():
    """订单表: 有关键列，日期已转换"""
    df = load_orders()
    assert len(df) > 0, "订单表不应为空"
    assert "order_date" in df.columns
    assert "order_month" in df.columns
    assert "customer_name" in df.columns
    assert "product_name" in df.columns
    assert "quantity" in df.columns
    assert "amount" in df.columns
    # 日期列必须是 datetime 类型
    assert pd.api.types.is_datetime64_any_dtype(df["order_date"]), "order_date 不是日期类型"
    # 金额不能为负
    assert (df["amount"] >= 0).all(), "存在负金额订单"


def test_load_inventory():
    """库存表: 无负库存"""
    df = load_inventory()
    assert len(df) > 0, "库存表不应为空"
    assert "current_stock" in df.columns
    assert (df["current_stock"] >= 0).all(), "存在负库存（未修复）"


def test_load_dealer_orders():
    """经销商订单: 从 Excel 加载，有 channel 标签"""
    df = load_dealer_orders()
    assert len(df) > 0, "经销商订单不应为空"
    assert "channel" in df.columns
    assert (df["channel"] == "经销商").all(), "channel 列应为'经销商'"
    assert "order_date" in df.columns
    assert "amount" in df.columns
    assert df["amount"].notna().all(), "存在空金额"
    assert (df["amount"] > 0).all(), "存在零或负金额"


def test_load_collections():
    """回款表: 有应收/已回/未回字段"""
    df = load_collections()
    assert len(df) > 0, "回款表不应为空"
    assert "receivable" in df.columns
    assert "collected" in df.columns
    assert "outstanding" in df.columns
    assert df["receivable"].notna().all(), "应收金额不应为空"


def test_dealer_orders_mergeable_with_orders():
    """经销商订单列结构必须与 MySQL 订单对齐，才能 pd.concat"""
    orders = load_orders()
    dealer = load_dealer_orders()
    common_cols = set(orders.columns) & set(dealer.columns)
    required = {"order_id", "order_date", "order_month", "customer_name",
                "product_name", "quantity", "amount"}
    missing = required - common_cols
    assert not missing, f"经销商订单缺少列: {missing}"
