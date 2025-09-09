"""
Email/OTP handling functions.
"""

import imaplib
import email
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import time
from config import PROTONMAIL_EMAIL, PROTONMAIL_PASSWORD, IMAP_SERVER, IMAP_PORT, SMTP_HOST, SMTP_PORT


def send_email(to_email, subject, body):
    username = PROTONMAIL_EMAIL
    password = PROTONMAIL_PASSWORD

    msg = MIMEMultipart()
    msg["From"] = username
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(username, password)
        server.sendmail(username, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")


def get_bls_consent_link(
    email_account=PROTONMAIL_EMAIL,
    password=PROTONMAIL_PASSWORD,
    imap_server=IMAP_SERVER,
    imap_port=IMAP_PORT,
    subject="BLS - Data Protection Information",
    check_interval=5
):
    """
    Connect to the IMAP server, search for an email with the given subject,
    parse its HTML body, locate the link "I have read and understood the information on data protection",
    and return that link as a string.

    Requirements:
      - pip install beautifulsoup4
      - Provide valid IMAP credentials and server info.

    :param email_account: Email address to log in
    :param password: IMAP account password
    :param imap_server: Hostname or IP of the IMAP server
    :param imap_port: Port for IMAP (default 1143 for local proxy)
    :param subject: Subject text to match (default "BLS - Data Protection Information")
    :param check_interval: How many seconds to wait between checks if not found
    :return: The found link as a string, or does not return until found
    """
    while True:
        try:
            mail = imaplib.IMAP4(imap_server, imap_port)
            mail.login(email_account, password)
            mail.select("INBOX")  

            search_criteria = f'(SUBJECT "{subject}")'
            status, email_ids = mail.search(None, search_criteria)
            if status == "OK" and email_ids[0]:
                arr = email_ids[0].split()
                latest_id = arr[-1]  
                fetch_status, data = mail.fetch(latest_id, "(RFC822)")

                if fetch_status == "OK" and data:
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    email_html = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            if ctype == "text/html":
                                email_html = part.get_payload(decode=True).decode(errors="ignore")
                                break
                            elif ctype == "text/plain" and not email_html:
                                email_html = part.get_payload(decode=True).decode(errors="ignore")
                    else:
                        email_html = msg.get_payload(decode=True).decode(errors="ignore")

                    soup = BeautifulSoup(email_html, "html.parser")
                    
                    link_tag = soup.find("a", text=re.compile("I have read and understood the information on data protection"))
                    if link_tag and link_tag.has_attr("href"):
                        found_link = link_tag["href"]
                        print("Found BLS consent link =>", found_link)

                        mail.store(latest_id, "+FLAGS", "\\Seen")
                        mail.logout()
                        return found_link

            mail.logout()
            time.sleep(check_interval)  

        except Exception as ex:
            print("IMAP error =>", ex)
            time.sleep(check_interval)


def get_otp(
    email_account=PROTONMAIL_EMAIL,
    password=PROTONMAIL_PASSWORD,
    imap_server=IMAP_SERVER,
    imap_port=IMAP_PORT,
    subject_contains="BLS Visa Appointment - Email Verification",
    check_interval=3
):
    """
    Connects to the IMAP server, searches for the latest email containing a specific subject,
    extracts the OTP from the email body, and returns the OTP as a string.
    """
    while True:
        try:
            print("searcing ... ")
            mail = imaplib.IMAP4(imap_server, imap_port)
            mail.login(email_account, password)
            mail.select("INBOX")

            status, email_ids = mail.search(None, f'(SUBJECT "{subject_contains}")')
            if status == "OK" and email_ids[0]:
                email_id_list = email_ids[0].split()
                latest_id = email_id_list[-1]  
                fetch_status, data = mail.fetch(latest_id, "(RFC822)")

                if fetch_status == "OK" and data:
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    email_text = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            if ctype in ["text/plain", "text/html"]:
                                email_text = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        email_text = msg.get_payload(decode=True).decode(errors="ignore")
                    
                    otp_match = re.search(r'\b(\d{6})\b', email_text)
                    if otp_match:
                        otp = otp_match.group(1)
                        print("Found OTP =>", otp)
                        
                        mail.store(latest_id, "+FLAGS", "\\Seen")
                        mail.logout()
                        return otp
            
            mail.logout()
            time.sleep(check_interval)  
        
        except Exception as ex:
            print("IMAP error =>", ex)
            time.sleep(check_interval)


def delete_all_protonmail_emails(email_account=PROTONMAIL_EMAIL, password="3miM_vVMuQVwQEG-BCpMlA"):
    try:
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        mail.login(email_account, password)
        for folder in ["inbox","Trash"]:
            mail.select(folder)
            _, nums = mail.search(None,"ALL")
            arr = nums[0].split()
            if arr:
                for n in arr:
                    mail.store(n,"+FLAGS","\\Deleted")
                mail.expunge()
                print(f"Deleted emails from {folder}")
            else:
                print(f"No emails in {folder}")
        mail.close()
        mail.logout()
        print("ProtonMail email cleanup done.")
    except Exception as ex:
        print("Error clearing mail =>", ex)