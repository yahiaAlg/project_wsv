"""
Configuration constants for BLS automation script.
"""

# API Configuration
API_KEY = "nourzed2024-7f03aab2-2b16-7b75-14ef-8da33f264137"
NOCAPTCHA_API_URL = "https://api.nocaptchaai.com/createTask"

# Login Credentials
EMAIL = "dzdz.shorthand731@passmail.net"
PASSWORD = "smsdztwsd0A"

# Email Configuration
PROTONMAIL_EMAIL = "blszedmas@pm.me"
PROTONMAIL_PASSWORD = "XwkKiEcFBt3-MZ6PT8XjVg"
IMAP_SERVER = "127.0.0.1"
IMAP_PORT = 1143
SMTP_HOST = "127.0.0.1"
SMTP_PORT = 1025

# Network Configuration
WIFI_INTERFACES = ["Wi-Fi 3", "Wi-Fi 4"]
wifi_interfaces = {
    "Wi-Fi 3": "p1",
    "Wi-Fi 4": "p2"
}
profile_paths = {
    "Wi-Fi 3": "C:\\Users\\mohamed\\Desktop\\1.xml",
    "Wi-Fi ": "C:\\Users\\mohamed\\Desktop\\2.xml"
}

# Tesseract Configuration
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Global Variables
current_index = 0
cat = None