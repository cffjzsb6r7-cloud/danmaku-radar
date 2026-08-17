# -*- coding: utf-8 -*-
"""邮件推送：SMTP（凭据走环境变量），支持纯文本 + HTML 双格式"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


def send_digest(to_emails, subject, text, html=None):
    host = os.environ.get("SMTP_HOST")
    if not host:
        print("[emailer] 未配置 SMTP_HOST，跳过发送")
        return 0
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM", user)
    sent = 0
    for email in to_emails:
        try:
            if html:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(text, "plain", "utf-8"))
                msg.attach(MIMEText(html, "html", "utf-8"))
            else:
                msg = MIMEText(text, "plain", "utf-8")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = sender
            msg["To"] = email
            if port == 465:
                s = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                s = smtplib.SMTP(host, port, timeout=20)
            if user:
                s.login(user, password)
            s.sendmail(sender, [email], msg.as_string())
            s.quit()
            sent += 1
        except Exception as e:
            print(f"[emailer] 发送失败 {email}: {e}")
    return sent
