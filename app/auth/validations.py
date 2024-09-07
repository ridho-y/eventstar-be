from . import auth_db
from ..exceptions import InvalidInputException, NotUniqueException
from pyhibp import pwnedpasswords as pw
from ..helpers import is_email
from .. import constants as c

import pyhibp

# ------------------------------------------------------------------------------------------------- #
# --------------------------- Sign-up field Constraint Validations -------------------------------- #


def validate_username(username: str) -> None:
    """
    Validate the provided username.

    Args:
        username (str): The username to validate.
        db (Session): The database session object.

    Returns:
        None

    Raises:
        InvalidInputException: If the username does not meet the validation criteria.
        NotUniqueException: If the username is already taken.
    """
    # check username length
    if not username or not (c.MIN_USERNAME_LEN <= len(username) <= c.MAX_USERNAME_LEN):
        raise InvalidInputException(
            f"Username must be between {c.MIN_USERNAME_LEN} and {c.MAX_USERNAME_LEN} characters in length."
        )

    # check if username
    if not username.isalnum():
        raise InvalidInputException("Username must contian only alpha-numeric characters.")

    # check if username is unique
    if not auth_db.username_is_unique(username):
        raise NotUniqueException(f"Username '{username}' is already taken.")


def validate_email(email: str) -> None:
    """
    Validate the provided email.

    Args:
        email (str): The email to validate.
        db (Session): The database session object.

    Returns:
        None

    Raises:
        InvalidInputException: If the email does not meet the validation criteria.
        NotUniqueException: If the email is already associated with an account.
    """
    if not email or not is_email(email):
        raise InvalidInputException("Invalid email syntax.")

    if not auth_db.email_is_unique(email):
        raise NotUniqueException(f"The email {email} is already associated with an account.")


def validate_password(username: str, password: str) -> None:
    """
    Validate the provided password.

    Args:
        username (str): The username.
        password (str): The password to validate.

    Returns:
        None

    Raises:
        InvalidInputException: If the password does not meet the validation criteria.
    """
    if not password or not (c.MIN_PASSWORD_LEN <= len(password) <= c.MAX_USERNAME_LEN):
        raise InvalidInputException(
            f"Passwords must be between {c.MIN_PASSWORD_LEN} and {c.MAX_USERNAME_LEN} characters in length."
        )

    # Check if password contains the username
    if username in password:
        raise InvalidInputException("Password must not include the username.")

    # Check if password has been breached
    pyhibp.set_user_agent(ua="EventStar")
    if pw.is_password_breached(password):
        raise InvalidInputException("This password has been breached online. Please choose another password.")

    if len(username) >= c.INVALID_USERNAME_PASSWORD_SUBSTR_LEN:
        for i in range(len(password) - c.INVALID_USERNAME_PASSWORD_SUBSTR_LEN):
            substring = password[i : i + c.INVALID_USERNAME_PASSWORD_SUBSTR_LEN + 1]
            if substring in username:
                raise InvalidInputException("Password cannot contain a substring of username.")


def validate_member_type(member_type: str) -> None:
    if member_type not in [c.CUSTOMER, c.HOST]:
        raise InvalidInputException("The provided member type is invalid.")
