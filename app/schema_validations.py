from fastapi import HTTPException

from . import constants
from datetime import date, datetime
from app import helpers
import re


def validate_memberType(cls, member_type):
    if member_type not in [constants.CUSTOMER, constants.HOST]:
        raise HTTPException(status_code=400, detail="MemberType must be one of 'user', or 'host'.")
    return member_type


def validate_email(cls, email):
    if not helpers.is_email(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    return email


def validate_optional_email(cls, opt_email):
    if opt_email and not helpers.is_email(opt_email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    return opt_email


def validate_phone(cls, phone):
    phone = re.sub(r"\D", "", phone)  # keep only digits
    pattern = r"^(\+?61|0)[2-478](?:[ -]?[0-9]){8}$"
    if not re.match(pattern, str(phone)):
        raise HTTPException(status_code=400, detail="Invalid Australian phone number")
    return phone


def validate_state(cls, state):
    states = ["nsw", "vic", "act", "qld", "tas", "sa", "wa", "nt"]
    if state.lower() not in states:
        raise HTTPException(status_code=400, detail="Invalid state")
    return state


def validate_country(cls, country):
    if country.lower() != "australia":
        raise HTTPException(status_code=400, detail="Country can only be Australia")
    return country.lower()


def validate_postcode(cls, postcode):
    pattern = r"^\d{4}$"
    if not re.match(pattern, str(postcode)):
        raise HTTPException(status_code=400, detail="Invalid Australian postcode")
    return postcode


def validate_expiry_month(cls, expiry_month):
    if int(expiry_month) not in range(1, 13):
        raise HTTPException(status_code=400, detail="Expiry month should be between 1 and 12")
    return expiry_month


def validate_card_number(cls, card_number):
    card_number = "".join(card_number.split())
    # Check for mastercard, visa and american express respectively
    card_regex = [
        r"^5[1-5][0-9]{14}|^(222[1-9]|22[3-9]\\d|2[3-6]\\d{2}|27[0-1]\\d|2720)[0-9]{12}$",
        r"^4[0-9]{12}(?:[0-9]{3})?$",
        r"^3[47][0-9]{13}$",
    ]
    if not helpers.match_any_pattern(str(card_number), card_regex) or len(str(card_number)) != 16:
        raise HTTPException(status_code=400, detail="Invalid card number")
    return card_number


def validate_expiry_year(cls, expiry_year, values):
    current_year = date.today().year

    if int(expiry_year) < current_year:
        raise HTTPException(status_code=400, detail="Expiry year must be in the future")

    return expiry_year


def validate_create_event_data(event_data: dict):
    required_fields = [
        "title",
        "description",
        "type",
        "startDateTime",
        "endDateTime",
        "ticketsAvailable",
        "minimumCost",
    ]

    for field in required_fields:
        if not event_data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} must not be empty")


def validate_event_type(cls, event_type):
    if event_type is None:
        return event_type
    if event_type not in ["inpersonSeated", "inpersonNonSeated", "online"]:
        raise HTTPException(status_code=400, detail="Invalid event")
    return event_type


def validate_date(cls, date):
    date_temp = date
    if type(date) == str:
        date_temp = datetime.fromisoformat(date)
    current_datetime = datetime.now()
    if current_datetime > date_temp:
        raise HTTPException(status_code=400, detail="Date must be in the future")
    date_temp = date
    return date_temp


def validate_rating(cls, rating):
    if rating < 0 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be in between 0 and 5")
    return rating


def validate_search(cls, search_str):
    if search_str == "":
        return search_str
    if not re.match(r"^[a-zA-Z0-9\s]+$", str(search_str)):
        raise HTTPException(status_code=400, detail="Search characters must be alphanumeric")
    return search_str


def validate_name(cls, name):
    if not re.match(r"^[a-zA-Z0-9\s]+$", str(name)) or len(str(name)) < 1:
        raise HTTPException(status_code=400, detail="Characters must be alphanumeric")
    return name


def validate_link(cls, link):
    url_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
    if not url_pattern.match(str(link)):
        raise HTTPException(status_code=400, detail=f"Invalid online link format '{link}'")
    return link


def validate_optLink(cls, optLink):
    url_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
    if not url_pattern.match(str(optLink)) and len(optLink) > 0:
        raise HTTPException(status_code=400, detail="Invalid online link format")
    return optLink


def validate_youtube_link(cls, link):
    url_pattern = re.compile(r"^(https?\:\/\/)?((www\.)?youtube\.com|youtu\.be)\/.+$")
    if not url_pattern.match(str(link)):
        raise HTTPException(status_code=400, detail="Invalid youtube link format")
    return link


def validate_long_string(cls, value):
    if len(value) > 5000:
        raise HTTPException(status_code=400, detail="This field is too long. Please enter less characters")
    return value


def validate_short_string(cls, value):
    if len(value) > 1000:
        raise HTTPException(status_code=400, detail="This field is too long. Please enter less characters")
    return value


def validate_react(cls, react):
    if react not in ["like", "dislike", "none"]:
        raise HTTPException(status_code=400, detail="React must be 'like' or 'dislike'")
    return react


def validate_required_string(cls, requiredStr):
    if len(requiredStr) < 5:
        raise HTTPException(status_code=400, detail="Must be greater than 5 characters.")
    return requiredStr


def validate_postive_int(cls, num):
    if num < 0:
        raise HTTPException(status_code=400, detail="Number must be positive")
    return num


def validate_message_type(cls, messageType):
    try:
        constants.EventChatRequest(messageType)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message Type.")
    return messageType
