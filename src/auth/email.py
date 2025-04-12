from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from typing import Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.config import get_settings

settings = get_settings()


class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.sender_email = settings.SENDER_EMAIL
        self.sender_password = settings.SMTP_PASSWORD
        self.template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def send_welcome_email(self, to_email: str, username: str) -> bool:
        template = self.env.get_template("welcome.html")
        html_content = template.render(username=username)
        return self._send_email(
            to_email=to_email,
            subject="¡Bienvenido a nuestra plataforma!",
            html_content=html_content
        )

    def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        reset_url = f"{settings.FRONTEND_URL}/auth/password-reset?token={reset_token}"
        template = self.env.get_template("password_reset.html")
        html_content = template.render(
            reset_url=reset_url,
            expiration_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        return self._send_email(
            to_email=to_email,
            subject="Restablecimiento de contraseña",
            html_content=html_content
        )
