# tools/email_tools.py
import smtplib
from email.mime.text import MIMEText

def send_email(smtp_server: str, smtp_port: int, username: str, password: str, from_addr: str, to_addr: str, subject: str, body: str):
    """
    Sends an email using SMTP over SSL.
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(username, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
