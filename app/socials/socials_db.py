from sqlalchemy.exc import IntegrityError
from datetime import datetime

from .. import constants, exceptions, models, schemas, helpers
from ..events import event_db
from ..database import db


# --------------------------------------------------------------------------------------- #
# ------------------------------- User Favourites --------------------------------------- #


def favourite_event(event_id: int, user_id: int) -> None:
    try:
        favourites = models.FavouritedEvent(
            customer_id=user_id,
            event_id=event_id
        )
        db.get().add(favourites)

    except IntegrityError:
        raise exceptions.InvalidInputException("This event has already been favourited.")

    except Exception:
        raise exceptions.BadGatewayException("Unable to favourite event. Please try again later.")


def is_event_favourited(event_id: int, user_id: int) -> bool:
    return (
        db.get()
        .query(models.FavouritedEvent)
        .filter(models.FavouritedEvent.customer_id == user_id)
        .filter(models.FavouritedEvent.event_id == event_id)
        .first()
        is not None
    )


# --------------------------------------------------------------------------------------- #
# ------------------------------- Event Reactions --------------------------------------- #


def get_user_event_reaction(event_id: int, user_id: int) -> bool:
    liked = user_liked_event(event_id, user_id)
    disliked = user_disliked_event(event_id, user_id)

    if liked:
        return constants.LIKE
    elif disliked:
        return constants.DISLIKE
    else:
        return constants.NONE


def user_liked_event(event_id: int, user_id: int) -> bool:
    return (
        db.get()
        .query(models.Like)
        .filter(models.Like.customer_id == user_id)
        .filter(models.Like.event_id == event_id)
        .first()
    ) is not None


def user_disliked_event(event_id: int, user_id: int) -> bool:
    return (
        db.get()
        .query(models.Dislike)
        .filter(models.Dislike.customer_id == user_id)
        .filter(models.Dislike.event_id == event_id)
        .first()
    ) is not None


def get_like_object(event_id: int, user_id: int):
    user_liked = (
        db.get()
        .query(models.Like)
        .filter(models.Like.customer_id == user_id)
        .filter(models.Like.event_id == event_id)
        .first()
    )

    return user_liked


def get_dislike_object(event_id: int, user_id: int):
    user_disliked = (
        db.get()
        .query(models.Dislike)
        .filter(models.Dislike.customer_id == user_id)
        .filter(models.Dislike.event_id == event_id)
        .first()
    )

    return user_disliked


# --------------------------------------------------------------------------------------- #
# ----------------------------------- Following ----------------------------------------- #


def user_follows_host(host_id: int, user_id: int):
    return (
        db.get()
        .query(models.Follower)
        .filter(models.Follower.host_id == host_id)
        .filter(models.Follower.customer_id == user_id)
        .first()
        is not None
    )


# ------------------------------------------------------------------------------------------------- #
# -------------------------------------- Event Announcements -------------------------------------- #


def make_announcement(announcement: schemas.Announcements, user: models.User) -> None:
    # Ensure that the event host is sending the request
    event_id = announcement.eventListingId
    event = event_db.get_event(event_id)
    if event.host_id != user.user_id:
        raise exceptions.ForbiddenAccessException("User does not have permission to make an announcement.")

    # Get all user emails
    email_list = event_db.get_event_customer_emails(event.event_id)
    if len(email_list) > 0:
        helpers.send_email_with_gmail(email_list, announcement.title, announcement.message)

    # Add the announcement in the  db
    new_announcement = models.EventAnnouncement(
        event_id=event_id,
        event_host=user.user_id,
        title=announcement.title,
        date=datetime.now(),
        message=announcement.message,
    )

    db.get().add(new_announcement)
