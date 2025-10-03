"""邮件发送服务。"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from src.logger import logger


class EmailService:
    """邮件发送服务类。"""

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None
    ):
        """初始化邮件服务。

        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            smtp_user: SMTP用户名
            smtp_password: SMTP密码
            from_email: 发件人邮箱
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email or smtp_user

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        """发送邮件。

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body_text: 纯文本邮件内容
            body_html: HTML邮件内容(可选)

        Returns:
            是否发送成功
        """
        try:
            # 如果未配置SMTP，记录警告并返回True(开发环境)
            if not self.smtp_user or not self.smtp_password:
                logger.warning(
                    f"SMTP未配置,邮件发送已跳过。\n"
                    f"收件人: {to_email}\n"
                    f"主题: {subject}\n"
                    f"内容: {body_text}"
                )
                return True

            # 创建邮件对象
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # 添加纯文本内容
            text_part = MIMEText(body_text, "plain", "utf-8")
            msg.attach(text_part)

            # 添加HTML内容(如果提供)
            if body_html:
                html_part = MIMEText(body_html, "html", "utf-8")
                msg.attach(html_part)

            # 连接SMTP服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"邮件已发送到 {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_code: str
    ) -> bool:
        """发送邮箱验证邮件。

        Args:
            to_email: 收件人邮箱
            username: 用户名
            verification_code: 验证码

        Returns:
            是否发送成功
        """
        subject = "LLM防护系统 - 邮箱验证"

        body_text = f"""
您好 {username},

感谢注册LLM防护系统!

您的邮箱验证码是: {verification_code}

此验证码将在30分钟后过期。

如果这不是您的操作,请忽略此邮件。

---
LLM防护系统团队
        """.strip()

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: white; padding: 30px; border: 1px solid #e1e8ed; border-top: none; }}
        .code-box {{ background: #f8f9fa; border: 2px solid #007AFF; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
        .code {{ font-size: 32px; font-weight: bold; color: #007AFF; letter-spacing: 5px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ LLM防护系统</h1>
            <p>邮箱验证</p>
        </div>
        <div class="content">
            <p>您好 <strong>{username}</strong>,</p>
            <p>感谢注册LLM防护系统!</p>
            <p>请使用以下验证码完成邮箱验证:</p>
            <div class="code-box">
                <div class="code">{verification_code}</div>
            </div>
            <p style="color: #666;">此验证码将在 <strong>30分钟</strong> 后过期。</p>
            <p style="color: #999; font-size: 14px;">如果这不是您的操作,请忽略此邮件。</p>
        </div>
        <div class="footer">
            <p>© 2024 LLM防护系统 | 保护您的AI应用安全</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        return await self.send_email(to_email, subject, body_text, body_html)

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_code: str
    ) -> bool:
        """发送密码重置邮件。

        Args:
            to_email: 收件人邮箱
            username: 用户名
            reset_code: 重置码

        Returns:
            是否发送成功
        """
        subject = "LLM防护系统 - 密码重置"

        body_text = f"""
您好 {username},

您请求重置LLM防护系统的密码。

您的密码重置验证码是: {reset_code}

此验证码将在30分钟后过期。

如果这不是您的操作,请立即登录系统检查账户安全。

---
LLM防护系统团队
        """.strip()

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: white; padding: 30px; border: 1px solid #e1e8ed; border-top: none; }}
        .code-box {{ background: #fff3cd; border: 2px solid #ffc107; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
        .code {{ font-size: 32px; font-weight: bold; color: #856404; letter-spacing: 5px; }}
        .warning {{ background: #f8d7da; border-left: 4px solid #dc3545; padding: 12px; margin: 20px 0; border-radius: 4px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 密码重置</h1>
            <p>LLM防护系统</p>
        </div>
        <div class="content">
            <p>您好 <strong>{username}</strong>,</p>
            <p>您请求重置密码。请使用以下验证码:</p>
            <div class="code-box">
                <div class="code">{reset_code}</div>
            </div>
            <p style="color: #666;">此验证码将在 <strong>30分钟</strong> 后过期。</p>
            <div class="warning">
                <strong>⚠️ 安全提示:</strong> 如果这不是您的操作,请立即登录系统检查账户安全,并联系管理员。
            </div>
        </div>
        <div class="footer">
            <p>© 2024 LLM防护系统 | 保护您的AI应用安全</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        return await self.send_email(to_email, subject, body_text, body_html)


# 创建全局邮件服务实例
email_service = EmailService()
