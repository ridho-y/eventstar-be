from datetime import datetime
import re
import string
import random
from typing import List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from fastapi import HTTPException
from .exceptions import BadGatewayException
from . import constants as c


def is_email(email: str) -> bool:
    """
    Check if the provided string is a valid email address.

    Args:
        email (str): The string to check.

    Returns:
        bool: True if the string is a valid email address, False otherwise.
    """
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(email_regex, email) is not None


def match_any_pattern(string, patterns):
    for pattern in patterns:
        if re.match(pattern, string):
            return True
    return False


def generate_code(length=c.DEFAULT_CODE_LENGTH):
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for i in range(length))


def send_email_with_gmail(to: List[str], subject: str, body: str):
    from_address = c.EVENTSTAR_EMAIL_ADDRESS
    password = c.EVENTSTAR_EMAIL_PASSWORD

    message = MIMEMultipart()
    message["From"] = from_address
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(c.EMAIL_HOST, c.EMAIL_PORT)
        server.starttls()
        server.login(from_address, password)
        server.sendmail(from_address, to, message.as_string())
        server.quit()
    except Exception:
        raise BadGatewayException("Failed to send email.")


def check_before_end_date(enddate):
    current_datetime = datetime.now()
    if current_datetime < enddate:
        raise HTTPException(status_code=400, detail="Event has not yet ended")


def verify_review_rating(rating):
    if rating < 0 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be in between 0 and 5")
