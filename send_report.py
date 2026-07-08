"""
报告发送模块 — 分析完成后自动发送邮件或钉钉通知
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_email(subject, body, to_emails=None):
    """发送邮件报告。从 .env 读取邮箱配置"""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not to_emails:
        to_emails = [smtp_user]  # 没指定收件人就发给自己

    if not smtp_host or not smtp_user:
        print(f"[通知] 邮件未配置，报告摘要:\n{body[:500]}")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP_SSL(smtp_host, 465, timeout=10)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_emails, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[邮件发送失败] {e}")
        return False


def summary_report(monthly, top_products, total_receivable, total_collected,
                   inv_alert_count=0, debt_top=None):
    """生成一份简洁的文字摘要，可发邮件或微信"""
    lines = [
        f"仲景堂月度销售摘要 — {datetime.now().strftime('%Y-%m-%d')}",
        "=" * 40,
    ]

    # 月度概况
    if len(monthly) > 0:
        latest = monthly.iloc[-1]
        best = monthly.loc[monthly["销售额"].idxmax()]
        lines.append(f"本月订单: {int(latest['订单数'])} 单 | 销售额: {latest['销售额']:,.0f} 元")
        lines.append(f"年度最高: {best['order_month']} | {best['销售额']:,.0f} 元")

    # 热销 TOP5
    if not top_products.empty:
        lines.append("\n热销产品 TOP5:")
        for i, (_, row) in enumerate(top_products.head(5).iterrows(), 1):
            lines.append(f"  {i}. {row['产品']} — {int(row['销量'])} 件 / {row['销售额']:,.0f} 元")

    # 回款
    if total_receivable > 0:
        rate = total_collected / total_receivable * 100
        lines.append(f"\n回款率: {rate:.1f}% | 已回: {total_collected:,.0f} | 未回: {total_receivable - total_collected:,.0f}")

    # 库存预警
    if inv_alert_count > 0:
        lines.append(f"\n库存预警: {inv_alert_count} 批次临期或过期，请通知仓库主管")

    # 欠款排行
    if debt_top is not None and len(debt_top) > 0:
        lines.append("\n需催收客户:")
        for _, row in debt_top.head(3).iterrows():
            lines.append(f"  {row['客户']} — 未回款 {row['未回款']:,.0f} 元")

    return "\n".join(lines)
