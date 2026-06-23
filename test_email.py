# test_email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def test_email():
    try:
        print("🔍 Testing SMTP Configuration...")
        print(f"Server: {SMTP_SERVER}:{SMTP_PORT}")
        print(f"Username: {SMTP_USERNAME}")
        print(f"Sender: {EMAIL_SENDER}")
        
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_SENDER
        msg['To'] = "your_test_email@gmail.com"  # Ganti dengan email untuk test
        msg['Subject'] = "Test Email from SIMDAMA"
        
        text = """
        Ini adalah email test dari SIMDAMA UNPAM.
        Konfigurasi SMTP Brevo berhasil!
        """
        
        html = """
        <html>
        <body>
            <h2>✅ Test Email Berhasil!</h2>
            <p>Ini adalah email test dari SIMDAMA UNPAM.</p>
            <p>Konfigurasi SMTP Brevo berhasil!</p>
            <hr>
            <small>Dikirim dari SIMDAMA UNPAM</small>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        print("📧 Menghubungkan ke SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.set_debuglevel(1)  # Tampilkan detail koneksi
        server.starttls()
        
        print("🔑 Login...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        print("📤 Mengirim email...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email berhasil dikirim!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_email()