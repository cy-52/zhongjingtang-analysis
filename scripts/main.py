"""
仲景堂医疗器械销售数据分析
连接公司 MySQL 数据库，直接写 SQL 提取数据并分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import time
import argparse

from config import RUN_MONTH, OUTPUT, CHARTS, setup_logging
from db_loader import (load_products, load_customers, load_orders,
                       load_inventory, load_collections, load_dealer_orders)

# ── 命令行 ──
parser = argparse.ArgumentParser(description="仲景堂医疗器械销售数据分析")
parser.add_argument("--month", "-m", type=str, default=RUN_MONTH, help=f"分析月份，默认当前({RUN_MONTH})")
parser.add_argument("--channel", "-c", type=str, default="全部", choices=["全部","金蝶","电商","经销商"],
                    help="只看哪个渠道？默认全部")
parser.add_argument("--report", "-r", type=str, default="full", choices=["full","sales","inventory","collection"],
                    help="报告类型：full=全部, sales=销售, inventory=库存, collection=回款")
parser.add_argument("--send", action="store_true", help="分析完成后自动发送邮件报告")
args = parser.parse_args()

logger = setup_logging("main")
start_time = time.time()
logger.info("=" * 60)
logger.info("===== 仲景堂医疗器械销售数据分析 =====")
logger.info(f"渠道过滤: {args.channel} | 报告类型: {args.report}")
logger.info(f"运行开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================
# 第1步：加载数据（自动连不同数据库）
# ============================================================
logger.info("===== 第1步：加载数据 =====")

products   = load_products()     # → 金蝶 MySQL
customers  = load_customers()    # → 金蝶 MySQL
db_orders  = load_orders()       # → 金蝶 MySQL（电商订单）
dealer_orders = load_dealer_orders()  # → Excel 文件（经销商）
inv        = load_inventory()    # → 金蝶 MySQL
coll       = load_collections()  # → 用友（另一套连接）

# 合并两个来源的订单 → 统一事实表
db_orders["channel"] = "电商"
all_orders = pd.concat([db_orders, dealer_orders], ignore_index=True)

coll["collected"] = coll["collected"].fillna(0)
coll["outstanding"] = coll["receivable"] - coll["collected"]
total_receivable = coll["receivable"].sum()
total_collected = coll["collected"].sum()
total_outstanding = coll["outstanding"].sum()

# ── 渠道过滤 ──
if args.channel != "全部":
    all_orders = all_orders[all_orders["channel"] == args.channel]
    logger.info(f"[过滤] 只看「{args.channel}」→ {len(all_orders)} 条")

logger.info(f"[加载] 产品: {len(products)} 种 | 客户: {len(customers)} 个")
logger.info(f"[加载] 订单: {len(all_orders)} 条（电商{len(db_orders)} + 经销商{len(dealer_orders)}）")
logger.info(f"[加载] 库存: {len(inv)} 条 | 回款: {len(coll)} 条 | 应收{total_receivable:,.0f}")

# ============================================================
# 第2步：分析（根据 --report 决定分析哪些维度）
# ============================================================
DO_SALES = args.report in ("full", "sales")
DO_INV   = args.report in ("full", "inventory")
DO_COLL  = args.report in ("full", "collection")
logger.info(f"===== 第2步：数据分析（销售:{DO_SALES} 库存:{DO_INV} 回款:{DO_COLL}）=====")

# 2.1 月度趋势
logger.info("  [1/8] 月度趋势")
monthly = (all_orders.groupby("order_month").agg(
    订单数=("order_id", "count"),
    销售额=("amount", "sum"),
    均单金额=("amount", "mean"),
).round(0).reset_index())

# 2.2 产品 Top10
logger.info("  [2/8] 产品排行")
top_products = (all_orders.groupby("product_name").agg(
    销量=("quantity", "sum"), 销售额=("amount", "sum")
).sort_values("销量", ascending=False).head(10).round(0).reset_index())
top_products.columns = ["产品", "销量", "销售额"]

# 2.3 品类排名
logger.info("  [3/8] 品类排名")
order_with_cat = all_orders.merge(products[["product_name", "category"]], on="product_name")
cat_stats = (order_with_cat.groupby("category").agg(
    订单数=("order_id", "count"), 销售额=("amount", "sum")
).sort_values("销售额", ascending=False).round(0).reset_index())
cat_stats.columns = ["品类", "订单数", "销售额"]

# 2.4 客户价值
logger.info("  [4/8] 客户价值")
cust_value = (all_orders.groupby("customer_name").agg(
    下单次数=("order_id", "count"), 累计消费=("amount", "sum")
).sort_values("下单次数", ascending=False).head(15).round(0).reset_index())
cust_value.columns = ["客户", "下单次数", "累计消费"]

# 2.5 月份环比
logger.info("  [5/8] 月份环比")
mom = monthly[["order_month", "销售额"]].copy()
mom.columns = ["月份", "销售额"]
mom["环比变化"] = mom["销售额"].pct_change() * 100
mom["环比变化"] = mom["环比变化"].round(1)

# 2.6 库存金额
logger.info("  [6/8] 库存分析")
if not inv.empty:
    inv["库存金额"] = inv["current_stock"] * inv["purchase_price"]
    inv_value = inv[["product_name", "current_stock", "purchase_price", "库存金额"]].copy()
    inv_value.columns = ["产品", "库存量", "进价", "库存金额"]
    inv_value = inv_value.sort_values("库存金额", ascending=False)

# 2.7 回款分析
logger.info("  [7/8] 回款分析")
if not coll.empty and total_receivable > 0:
    debt = (coll.groupby("customer_name").agg(
        未回款=("outstanding", "sum"), 应收=("receivable", "sum"), 已回=("collected", "sum")
    ).reset_index())
    debt["回款率"] = (debt["已回"] / debt["应收"] * 100).round(1)
    debt_top = debt[debt["未回款"] > 0].sort_values("未回款", ascending=False).head(10)

# 2.8 订单状态
logger.info("  [8/8] 订单状态")
order_status = all_orders.groupby("status").size().reset_index()
order_status.columns = ["状态", "数量"]

# 关键指标汇总
if len(monthly) > 0:
    best = monthly.loc[monthly["销售额"].idxmax()]
    logger.info(f"  >>> 月度最高: {best['order_month']} ({best['销售额']:,.0f}元)")
if not top_products.empty:
    logger.info(f"  >>> 产品TOP1: {top_products['产品'].iloc[0]} ({int(top_products['销量'].iloc[0])}件)")
if total_receivable > 0:
    logger.info(f"  >>> 回款率: {total_collected/total_receivable*100:.1f}%")

# ============================================================
# 第3步：可视化（8 张图）
# ============================================================
logger.info(f"===== 第3步：生成图表（销售:{DO_SALES} 库存:{DO_INV} 回款:{DO_COLL}）=====")

# 图1: 月度趋势
if DO_SALES:
 fig, ax1 = plt.subplots(figsize=(13, 5.5))
ax1.bar(monthly["order_month"].astype(str), monthly["订单数"], color="#4E79A7", alpha=0.85)
ax1.set_ylabel("订单数", color="#4E79A7"); ax1.tick_params(axis="x", rotation=45)
ax2 = ax1.twinx()
ax2.plot(monthly["order_month"].astype(str), monthly["均单金额"], color="#E15759", lw=2.5, marker="o", ms=6)
ax2.set_ylabel("均单金额(元)", color="#E15759")
plt.title("月度销售趋势", fontsize=15, fontweight="bold")
plt.tight_layout(); plt.savefig(CHARTS / "01_monthly_trend.png", dpi=150); plt.close()

# 图2: 产品Top10
fig, ax = plt.subplots(figsize=(12, 6))
t10 = top_products.sort_values("销量", ascending=True)
ax.barh(range(len(t10)), t10["销量"], color="#76B7B2")
ax.set_yticks(range(len(t10))); ax.set_yticklabels(t10["产品"].values, fontsize=10)
ax.set_xlabel("销量(件)"); ax.set_title("产品销量 Top 10", fontsize=15, fontweight="bold")
for i, v in enumerate(t10["销量"]): ax.text(v+0.5, i, f"{int(v)}", va="center", fontsize=9)
plt.tight_layout(); plt.savefig(CHARTS / "02_top_products.png", dpi=150); plt.close()

# 图3: 品类排名
fig, ax = plt.subplots(figsize=(10, 7))
cp = cat_stats.sort_values("销售额", ascending=True)
colors = ["#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F","#B07AA1"]
ax.barh(range(len(cp)), cp["销售额"], color=colors[:len(cp)])
ax.set_yticks(range(len(cp))); ax.set_yticklabels(cp["品类"].values, fontsize=10)
ax.set_xlabel("销售额(元)"); ax.set_title("各品类销售额排名", fontsize=15, fontweight="bold")
for i, v in enumerate(cp["销售额"]): ax.text(v+5, i, f"{v:,.0f}", va="center", fontsize=9)
plt.tight_layout(); plt.savefig(CHARTS / "03_category_sales.png", dpi=150); plt.close()

# 图4: 客户价值散点图
fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(cust_value["下单次数"], cust_value["累计消费"], s=cust_value["下单次数"]*40,
           c="#4E79A7", alpha=0.6, edgecolors="white")
ax.set_xlabel("下单次数"); ax.set_ylabel("累计消费(元)")
ax.set_title("客户价值分析", fontsize=15, fontweight="bold")
for _, r in cust_value.head(8).iterrows():
    ax.annotate(r["客户"], (r["下单次数"], r["累计消费"]), fontsize=9)
plt.tight_layout(); plt.savefig(CHARTS / "04_customer_value.png", dpi=150); plt.close()

# 图5: 月度环比
fig, ax = plt.subplots(figsize=(12, 5.5))
x = range(len(mom))
ax.bar(x, mom["销售额"], color="#4E79A7", alpha=0.85)
ax.set_xticks(x); ax.set_xticklabels(mom["月份"].values, rotation=45)
for i, (_, r) in enumerate(mom.iterrows()):
    change = r["环比变化"]
    color = "#E15759" if (pd.notna(change) and change < 0) else "#59A14F"
    label = f"{change:+.1f}%" if pd.notna(change) else ""
    ax.text(i, r["销售额"]+max(mom["销售额"])*0.02, label, ha="center", color=color, fontsize=10, fontweight="bold")
ax.set_title("月度销售额 & 环比变化", fontsize=15, fontweight="bold")
plt.tight_layout(); plt.savefig(CHARTS / "05_month_over_month.png", dpi=150); plt.close()

# 图6: 订单状态
fig, ax = plt.subplots(figsize=(8, 6))
ax.pie(order_status["数量"], labels=order_status["状态"], autopct="%1.1f%%",
       colors=["#59A14F","#E15759","#F28E2B"], startangle=90, textprops={"fontsize":11})
ax.set_title("订单状态分布", fontsize=15, fontweight="bold")
plt.tight_layout(); plt.savefig(CHARTS / "06_order_status.png", dpi=150); plt.close()

# 图7: 库存金额
if not inv.empty:
    fig, ax = plt.subplots(figsize=(12, 6))
    iv_top = inv_value.head(10).sort_values("库存金额", ascending=True)
    ax.barh(range(len(iv_top)), iv_top["库存金额"], color="#F28E2B", alpha=0.85)
    ax.set_yticks(range(len(iv_top))); ax.set_yticklabels(iv_top["产品"].values, fontsize=10)
    ax.set_xlabel("库存金额(元)"); ax.set_title("库存金额 Top 10", fontsize=15, fontweight="bold")
    for i, v in enumerate(iv_top["库存金额"]): ax.text(v+5, i, f"{v:,.0f}", va="center", fontsize=9)
    plt.tight_layout(); plt.savefig(CHARTS / "07_inventory_value.png", dpi=150); plt.close()

# 图8: 回款排行
if not coll.empty and not debt_top.empty:
    fig, ax = plt.subplots(figsize=(12, 6))
    d5 = debt_top.sort_values("未回款", ascending=True)
    ax.barh(range(len(d5)), d5["未回款"], color="#E15759", alpha=0.85)
    ax.set_yticks(range(len(d5))); ax.set_yticklabels(d5["客户"].values, fontsize=10)
    ax.set_xlabel("未回款(元)"); ax.set_title("客户欠款排行", fontsize=15, fontweight="bold")
    for i, v in enumerate(d5["未回款"]): ax.text(v+5, i, f"{v:,.0f}", va="center", fontsize=9)
    plt.tight_layout(); plt.savefig(CHARTS / "08_outstanding_debt.png", dpi=150); plt.close()

logger.info(f"  图表已保存到 {CHARTS}")

# ============================================================
# 第4步：生成报告
# ============================================================
logger.info("===== 第4步：生成分析报告 =====")

total_sales = all_orders["amount"].sum()
report = f"""# 仲景堂医疗器械销售数据分析报告

> **分析日期**: {datetime.now().strftime('%Y-%m-%d')}
> **数据来源**: 公司 MySQL 数据库 (mugwort)
> **总销售额**: {total_sales:,.0f} 元 | **总订单**: {len(all_orders):,} 条 | **产品**: {len(products)} 种 | **客户**: {len(customers)} 个

---

## 一、月度销售趋势 & 环比
![月度趋势](charts/01_monthly_trend.png)
![环比](charts/05_month_over_month.png)

## 二、产品销量 Top 10
![产品排行](charts/02_top_products.png)

## 三、品类销售额排名
![品类排名](charts/03_category_sales.png)

## 四、客户价值分析
![客户价值](charts/04_customer_value.png)

## 五、订单状态分布
![订单状态](charts/06_order_status.png)

## 六、库存分析
![库存金额](charts/07_inventory_value.png)

## 七、回款催收
![欠款排行](charts/08_outstanding_debt.png)

## 八、运营建议
1. 关注环比下降月份，排查是季节性因素还是竞品冲击
2. 高库存金额产品优先促销，降低资金占用
"""

(OUTPUT / "analysis_report.md").write_text(report, encoding="utf-8")

# ── 发送报告 ──
if args.send:
    logger.info("===== 发送报告 =====")
    from send_report import summary_report, send_email
    summary = summary_report(monthly, top_products, total_receivable, total_collected)
    subject = f"仲景堂销售月报 — {datetime.now().strftime('%Y年%m月')}"
    send_email(subject, summary)
    logger.info(f"  报告摘要:\n{summary}")

# ── 汇总 ──
total_time = time.time() - start_time
logger.info(f"  → {OUTPUT / 'analysis_report.md'}")
logger.info(f"===== 分析完成 =====")
logger.info(f"  总耗时: {total_time:.1f}秒")
