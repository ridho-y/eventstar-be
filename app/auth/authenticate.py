from datetime import datetime, timedelta
import os
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from itsdangerous import URLSafeTimedSerializer

from . import auth_db
from .. import schemas, models, helpers, constants as c
from app.exceptions import NotFoundException, InvalidInputException
from typing import Union

# ------------------------------------------------------------------------------------------------- #
# ------------------------------------ Authentication --------------------------------------------- #

SECRET_KEY = os.environ.get("SERIALIZER_SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT", auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

email_serializer = URLSafeTimedSerializer(SECRET_KEY)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if a plain password matches the hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_string(string: str):
    """
    Hash a string using bcrypt.
    """
    return pwd_context.hash(string)


def authenticate_user(username_or_email: str, password: str):
    user = auth_db.get_user_from_username_or_email(username_or_email)
    if not user or not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict) -> str:
    """
    Create an access token with the provided JWT data.
    """
    data["expire"] = (datetime.utcnow() + timedelta(minutes=c.ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ------------------------------------------------------------------------------------------------- #
# -------------------------------- Get User from Auth Token  -------------------------------------- #


def get_user_or_none(token: Union[str, None] = Depends(oauth2_scheme)) -> models.User:
    """
    Get the current authenticated user based on the provided token.

    Args:
        db (Session): The database session object.
        token (str, optional): The access token. Defaults to Depends(oauth2_scheme).

    Returns:
        schemas.User: The User object of the authenticated user.

    Raises:
        HTTPException: If the credentials cannot be validated.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload:
            return None
        token_data = schemas.JWTToken(
            memberId=payload["member_id"],
            memberType=payload["member_type"],
            expiry=payload["expire"]
        )
    except JWTError:
        return None

    try:
        user = auth_db.get_user_from_id(token_data.memberId)
    except Exception:
        return None

    # Check if user exists and is still active
    if not user or not user.active:
        return None

    # Check if token is expired
    expire_time = datetime.fromisoformat(payload["expire"])
    current_time = datetime.utcnow()

    if expire_time < current_time:
        return None

    return user


def get_current_user(user: Union[str, None] = Depends(get_user_or_none)) -> models.User:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "bearer"},
    )
    if not user:
        raise credential_exception

    return user


# ------------------------------------------------------------------------------------------------------ #
# -------------------------------------- Reset Password ------------------------------------------------ #


def send_reset_code_to_email(email: str) -> None:
    if not email.email or not helpers.is_email(email.email):
        raise InvalidInputException("Invalid email syntax.")

    try:
        user = auth_db.get_user_by_email(email.email)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    # get new reset code
    reset_code = helpers.generate_code()

    # update the reset code so user cant use the same reset code
    auth_db.update_reset_code(user, reset_code)
    # email
    # no site to redirect user to yet lol..
    body = f"Your reset code is {reset_code}"
    # Add "Please follow the link to reset your password: http://website.com/reset-password/{token}" when site is up
    helpers.send_email_with_gmail([user.email], "Password reset request", body)

    return {}


def check_reset_code(user: models.User, reset_code: str):
    if user.reset_code != reset_code:
        return False

    reset_duration = timedelta(minutes=10)
    if datetime.now() >= user.reset_password_timer + reset_duration:
        return False

    return True
