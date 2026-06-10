"""Email sender for analysis reports."""

from __future__ import annotations

import logging
import os
import smtplib
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

from tradingagents.utils.time_utils import now_beijing_str

logger = logging.getLogger(__name__)


SMTP_CONFIGS = {
    "qq.com": {"server": "smtp.qq.com", "port": 465, "ssl": True},
    "foxmail.com": {"server": "smtp.qq.com", "port": 465, "ssl": True},
    "163.com": {"server": "smtp.163.com", "port": 465, "ssl": True},
    "126.com": {"server": "smtp.126.com", "port": 465, "ssl": True},
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "ssl": False},
    "outlook.com": {"server": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "hotmail.com": {"server": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "live.com": {"server": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "sina.com": {"server": "smtp.sina.com", "port": 465, "ssl": True},
    "sohu.com": {"server": "smtp.sohu.com", "port": 465, "ssl": True},
    "aliyun.com": {"server": "smtp.aliyun.com", "port": 465, "ssl": True},
    "139.com": {"server": "smtp.139.com", "port": 465, "ssl": True},
}


def send_email_with_attachments(
    subject: str,
    body: str,
    receivers: list[str],
    sender: str,
    password: str,
    sender_name: str = "A股投研分析",
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Send email with optional attachments.

    Args:
        subject: Email subject
        body: Email body (plain text)
        receivers: List of receiver email addresses
        sender: Sender email address
        password: SMTP password/authorization code
        sender_name: Display name for sender
        attachments: List of (filename, content_bytes, mime_type) tuples
        timeout: SMTP connection timeout in seconds

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not sender or not password:
        return False, "邮箱配置不完整"

    if not receivers:
        return False, "未指定收件人"

    server: Optional[smtplib.SMTP] = None

    try:
        msg = MIMEMultipart()
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((str(Header(sender_name, "utf-8")), sender))
        msg["To"] = ", ".join(receivers)

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachments:
            for filename, content, mime_type in attachments:
                part = MIMEApplication(content, _subtype=mime_type.split("/")[-1])
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

        domain = sender.split("@")[-1].lower()
        smtp_config = SMTP_CONFIGS.get(domain)

        if smtp_config:
            smtp_server = smtp_config["server"]
            smtp_port = smtp_config["port"]
            use_ssl = smtp_config["ssl"]
        else:
            smtp_server = f"smtp.{domain}"
            smtp_port = 465
            use_ssl = True
            logger.warning(f"未知邮箱类型 {domain}，尝试通用配置")

        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=timeout)
            server.starttls()

        server.login(sender, password)
        server.send_message(msg)

        logger.info(f"邮件发送成功，收件人: {receivers}")
        return True, "发送成功"

    except smtplib.SMTPAuthenticationError:
        return False, "认证失败，请检查邮箱和授权码"
    except smtplib.SMTPConnectError as e:
        return False, f"无法连接SMTP服务器: {e}"
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False, f"发送失败: {e}"
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass


def send_analysis_report(
    ticker: str,
    trade_date: str,
    stock_name: str,
    signal: str,
    md_content: str,
    pdf_bytes: bytes,
    sender: str,
    password: str,
    receivers: list[str],
) -> tuple[bool, str]:
    """Send analysis report via email.

    Args:
        ticker: Stock ticker code
        trade_date: Analysis date
        stock_name: Stock name
        signal: Trading signal
        md_content: Markdown report content
        pdf_bytes: PDF report bytes
        sender: Sender email
        password: SMTP password
        receivers: List of receiver emails

    Returns:
        Tuple of (success: bool, message: str)
    """
    name_suffix = f"_{stock_name}" if stock_name else ""
    file_prefix = f"{ticker}{name_suffix}_{trade_date}"

    subject = f"📈 A股投研分析报告 - {ticker}{name_suffix} ({trade_date})"

    body = f"""A股投研分析报告

股票代码: {ticker}
股票名称: {stock_name or '未知'}
分析日期: {trade_date}
交易信号: {signal.upper()}
生成时间: {now_beijing_str('%Y-%m-%d %H:%M:%S')}

报告详情请查看附件。

---
本报告由 AI 自动生成，仅供学习研究，不构成投资建议。
"""

    attachments = [
        (f"{file_prefix}.md", md_content.encode("utf-8"), "text/markdown"),
        (f"{file_prefix}.pdf", pdf_bytes, "application/pdf"),
    ]

    return send_email_with_attachments(
        subject=subject,
        body=body,
        receivers=receivers,
        sender=sender,
        password=password,
        attachments=attachments,
    )
