import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

def send_price_alert(product_name, price_per_oz, recipient_email, url):
    """Send email alert when price is below threshold"""
    try:
        sender_email = os.getenv("GMAIL_EMAIL")
        sender_password = os.getenv("GMAIL_PASS")
        
        # Convert price_per_oz to float
        price_per_oz = float(price_per_oz)

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = f"Price Alert: {product_name}"
        
        body = f"{product_name} is now ${price_per_oz:.2f} per ounce at {url}"
        message.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print("Email sent successfully!")
        
    except ValueError as e:
        print(f"Error converting price to float: {e}")
    except smtplib.SMTPAuthenticationError:
        print("Error: Gmail credentials are incorrect")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")