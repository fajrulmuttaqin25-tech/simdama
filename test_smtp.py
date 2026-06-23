# test_smtp.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

# Ambil dari environment
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def test_smtp():
    print("="*50)
    print("TESTING SMTP CONFIGURATION")
    print("="*50)
    print(f"SMTP_SERVER: {SMTP_SERVER}")
    print(f"SMTP_PORT: {SMTP_PORT}")
    print(f"SMTP_USERNAME: {SMTP_USERNAME}")
    print(f"EMAIL_SENDER: {EMAIL_SENDER}")
    print(f"SMTP_PASSWORD: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'NOT SET'}")
    print("="*50)
    
    if not all([SMTP_USERNAME, SMTP_PASSWORD, EMAIL_SENDER]):
        print("❌ ERROR: Ada environment variable yang belum diisi!")
        print("   Pastikan .env file berisi semua variabel yang diperlukan")
        return False
    
    try:
        # Test email ke email Anda sendiri
        test_email = input("Masukkan email untuk test (atau tekan Enter untuk skip): ").strip()
        if not test_email:
            print("⚠️  Test email skipped")
            return True
            
        # Buat email
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_SENDER
        msg['To'] = test_email
        msg['Subject'] = "✅ Test SMTP Brevo - SIMDAMA"
        
        text = """
        Test SMTP Brevo berhasil!
        
        Ini adalah email test dari SIMDAMA UNPAM.
        
        Konfigurasi:
        - Server: smtp-relay.brevo.com
        - Port: 587
        - Username: {}
        """.format(SMTP_USERNAME)
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #0d6efd;">✅ Test SMTP Brevo Berhasil!</h2>
            <p>Ini adalah email test dari <b>SIMDAMA UNPAM</b>.</p>
            <p>Konfigurasi SMTP:</p>
            <ul>
                <li><b>Server:</b> smtp-relay.brevo.com</li>
                <li><b>Port:</b> 587</li>
                <li><b>Username:</b> {SMTP_USERNAME}</li>
            </ul>
            <hr>
            <small style="color: #888;">Dikirim dari SIMDAMA UNPAM</small>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        print("\n📧 Menghubungkan ke SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.set_debuglevel(0)  # Set ke 1 untuk melihat detail
        
        print("🔒 Mengaktifkan TLS...")
        server.starttls()
        
        print("🔑 Login ke Brevo...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        print(f"📤 Mengirim email ke {test_email}...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email berhasil dikirim!")
        print(f"📧 Cek inbox/spam di {test_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ AUTHENTICATION ERROR: {str(e)}")
        print("\n   Kemungkinan penyebab:")
        print("   1. SMTP_USERNAME bukan email Brevo yang benar")
        print("   2. SMTP_PASSWORD bukan SMTP key yang benar")
        print("   3. SMTP key sudah expired atau tidak aktif")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP ERROR: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    test_smtp()