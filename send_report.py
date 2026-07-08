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

    if not smtp_host or not smtp_user:
        print(f"[通知] 邮件未配置（SMTP_HOST 为空），报告已生成但未发送")
        print(f"[通知] 报告摘要:\n{body[:500]}")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_emails or [])
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_host, 587, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_emails, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[邮件发送失败] {e}")
        return False


def summary_report(monthly, top_products, total_receivable, total_collected):
    """生成一份简洁的文字摘要，可以发邮件或发微信"""
    lines = [
        f"仲景堂月度销售摘要 — {datetime.now().strftime('%Y-%m-%d')}",
        "=" * 40,
    ]
    if len(monthly) > 0:
        latest = monthly.iloc[-1]
        best = monthly.loc[monthly["销售额"].idxmax()]
        lines.append(f"本月订单: {int(latest['订单数'])} 单 | 销售额: {latest['销售额']:,.0f} 元")
        lines.append(f"年度最高: {best['order_month']} | {best['销售额']:,.0f} 元")

    if not top_products.empty:
        tp = top_products.iloc[0]
        lines.append(f"热销TOP1: {tp['产品']}（{int(tp['销量'])} 件 / {tp['销售额']:,.0f} 元）")

    if total_receivable > 0:
        rate = total_collected / total_receivable * 100
        lines.append(f"回款率: {rate:.1f}% | 已回: {total_collected:,.0f} | 未回: {total_receivable - total_collected:,.0f}")

    return "\n".join(lines)
