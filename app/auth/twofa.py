import pyotp
from .. import models
from ..exceptions import InvalidRequestException
from . import auth_db


def enable_2fa(user: models.User) -> str:
    """
    Enable two-factor authentication for a user.

    Args:
        user (models.User): The user model object.
        db (Session): The database session object.

    Returns:
        str: The generated two-factor authentication code.

    Raises:
        InvalidRequestException: If two-factor authentication is already enabled for the user.
    """
    # Check if user already has 2fa
    if user.twofa_enabled:
        raise InvalidRequestException("Two factor authentication is already enabled for your account.")
    # Generate two factor authentication code and store
    twofa_key = pyotp.random_base32()
    user.two_fa_code = twofa_key
    user.twofa_enabled = True
    return twofa_key


def disable_2fa(user: models.User) -> str:
    """
    Disables two-factor authentication for a user.

    Args:
        user (models.User): The user model object.
        db (Session): The database session object.

    Raises:
        InvalidRequestException: If two-factor authentication is already disabled for the user.
    """
    # Check if user already doesnt have 2fa
    if not user.twofa_enabled:
        raise InvalidRequestException("Two factor authentication is not enabled for your account.")
    user.twofa_enabled = False


def verify_otp(user: models.User, otp: str) -> bool:
    """
    Verify the provided time based one-time password (TOTP) for a user.

    Args:
        user (models.User): The user model object.
        otp (str): The one-time password to verify.
        db (Session): The database session object.

    Returns:
        bool: True if the OTP is valid, False otherwise.
    """
    # Generate TOTP
    generated_otp = pyotp.TOTP(user.two_fa_code).now()
    if otp == generated_otp:
        return True
    else:
        return False
