from datetime import datetime
from typing import Union
from sqlalchemy.orm.exc import NoResultFound

from .. import exceptions, models, schemas, constants
from ..database import db
from ..helpers import is_email
from .authenticate import hash_string
from .validations import validate_password


# --------------------------------------------------------------------------------------- #
# ----------------------------------- Register User ------------------------------------- #


def register_user(input: schemas.SignUpRequest) -> None:
    if input.memberType == constants.CUSTOMER:
        user = models.Customer(
            first_name=input.firstName,
            last_name=input.lastName,
            username=input.username,
            email=input.email,
            password=hash_string(input.password),
            user_type=input.memberType,
        )
        db.get().add(user)
    else:
        user = models.Host(
            first_name=input.firstName,
            last_name=input.lastName,
            username=input.username,
            email=input.email,
            password=hash_string(input.password),
            user_type=input.memberType,
        )
        db.get().add(user)


# --------------------------------------------------------------------------------------- #
# ----------------------------------- Get Users ----------------------------------------- #


def get_user_from_id(user_id: int) -> models.User:
    try:
        user = db.get().query(models.User).filter(models.User.user_id == user_id).first()
    except Exception:
        raise exceptions.NotFoundException(f"User with id '{user_id}' not found.")

    return user


def get_user_by_email(email: str) -> models.User:
    try:
        return db.get().query(models.User).filter(models.User.email == email).first()
    except Exception:
        raise exceptions.NotFoundException(f"Could not retrieve user with email '{email}'.")


def get_user_by_reset_code(reset_code: str) -> models.User:
    try:
        user = db.get().query(models.User).filter(models.User.reset_code == reset_code).first()
    except Exception:
        return False
    return user


def get_user_from_username_or_email(username_or_email: str) -> Union[models.User, bool]:
    """
    Retrieve a user from the database based on the username or email.

    Args:
        db (Session): The database session object.
        username_or_email (str): The username or email of the user to retrieve.

    Returns:
        Union[models.User, bool]: The User object if found, or False if the user is not found.

    Raises:
        None
    """
    login_type_entry = models.User.email if is_email(username_or_email) else models.User.username
    try:
        user = db.get().query(models.User).filter(login_type_entry == username_or_email).one()
    except Exception:
        return False

    return user


# ---------------------------------------------------------------------------------------------- #
# ----------------------------------- Auth Validations ----------------------------------------- #


def username_is_unique(username: str) -> bool:
    """
    Check if a username is unique in the database.

    Args:
        db (Session): The database session object.
        username (str): The username to check.

    Returns:
        bool: True if the username is unique, False otherwise.

    Raises:
        None
    """
    try:
        db.get().query(models.User).filter(models.User.username == username).one()
        return False  # Username already exists, not unique
    except NoResultFound:
        return True  # Username is unique


def email_is_unique(email: str) -> bool:
    """
    Check if an email is unique in the database.

    Args:
        db (Session): The database session object.
        email (str): The email to check.

    Returns:
        bool: True if the email is unique, False otherwise.

    Raises:
        None
    """
    try:
        db.get().query(models.User).filter(models.User.email == email).one()
        return False  # Username already exists, not unique
    except NoResultFound:
        return True  # Username is unique


# ---------------------------------------------------------------------------------------------- #
# ----------------------------------- Reset Password ------------------------------------------- #


def check_reset_code(reset_code: str):
    # user already exists if want to reset pass
    try:
        db.get().query(models.User).filter(models.User.reset_code == reset_code).first()
    except NoResultFound:
        return False
    return True


def update_reset_code(user: models.User, reset_code: str):
    user.reset_code = reset_code
    user.reset_password_timer = datetime.now()


def clear_reset_code(user: models.User):
    user.reset_code = None
    db.get().flush()


def update_password(user: models.User, new_password: str):
    validate_password(user.username, new_password)
    user.password = hash_string(new_password)
    db.get().flush()


# ---------------------------------------------------------------------------------------------- #
# ----------------------------------- miscellaneous -------------------------------------------- #


def check_user_is_host(user: models.User, event_id: int):
    return (
        db.get()
        .query(models.Event)
        .filter(models.Event.host_id == user.user_id)
        .filter(models.Event.event_id == event_id)
        .first()
    )
