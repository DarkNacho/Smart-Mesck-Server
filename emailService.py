import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from email import encoders

class Message:
    def __init__(self, sender : str, recipients: list[str], subject: str):
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        self.msg = MIMEMultipart()

    def set_body(self, body):
        self.msg.attach(MIMEText(body))

    def add_attachment(self, filename, attachment_stream):
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_stream.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.msg.attach(part)

    def add_attachments(self, attachments):
        for filename, attachment_stream in attachments:
            attachment_stream.seek(0)
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_stream.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.msg.attach(part)
            
    def to_msg(self):
        self.msg['From'] = self.sender
        self.msg['To'] = COMMASPACE.join(self.recipients)
        self.msg['Subject'] = self.subject
        return self.msg


class EmailService:
    def __init__(self, smtp_server:str, port:int, username:str, password:str):
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password

    def send_mail(self, message):
        server = smtplib.SMTP(self.smtp_server, self.port)

        server.starttls()
        server.login(self.username, self.password)

        server.sendmail(message.sender, message.recipients, message.to_msg().as_string())
        server.quit()
        
        
        
NAME="Taryn Volkman"
USER="taryn.volkman66@ethereal.email"
PASS="wnQ2QmavuSdNcVWS5g"
HOST="smtp.ethereal.email"
PORT=587


async def send_email(recipients: list[str] , subject: str, body):
    msg = Message(sender=USER, recipients=recipients, subject=subject)
    msg.set_body(body)
    mail_service = EmailService(HOST, PORT, USER, PASS)
    await mail_service.send_mail(msg)


if __name__ == "__main__":
    msg = Message(sender=USER, recipients=["destinatario@example.com", "nacho@nacho.cl"], subject="¡Hola!")
    msg.set_body("Este es un correo de prueba.")

    mail_service = EmailService(HOST, PORT, USER, PASS)
    mail_service.send_mail(msg)