from .. import models, schemas, constants, exceptions
from ..database import db
from ..events import event_preview
from . import socials_db


def get_user_favourites(user: models.User) -> schemas.EventListingPreviewList:

    if user.user_type != constants.CUSTOMER:
        raise exceptions.ForbiddenAccessException("Only customers can favourite events.")

    return schemas.EventListingPreviewList(
        eventListings=[
            event_preview.get_event_preview(favourited_event.event)
            for favourited_event in user.customer.favourited_events
        ]
    )


def like_event(event_id: int, user_id: int) -> None:
    if socials_db.get_like_object(event_id, user_id):
        return

    user_disliked = socials_db.get_dislike_object(event_id, user_id)
    if user_disliked:
        db.get().delete(user_disliked)

    like = models.Like(customer_id=user_id, event_id=event_id)

    db.get().add(like)


def dislike_event(event_id: int, user_id: int) -> None:
    if socials_db.get_dislike_object(event_id, user_id):
        return

    user_liked = socials_db.get_like_object(event_id, user_id)

    if user_liked:
        db.get().delete(user_liked)

    dislike = models.Dislike(customer_id=user_id, event_id=event_id)

    db.get().add(dislike)


def unreact_event(event_id: int, user_id: int) -> None:
    user_liked = socials_db.get_like_object(event_id, user_id)
    user_disliked = socials_db.get_dislike_object(event_id, user_id)

    if user_liked is None and user_disliked is None:
        return

    elif user_liked is None and user_disliked:
        db.get().delete(user_disliked)

    else:
        db.get().delete(user_liked)


def react_to_event(event_id: int, user: models.User, react: str) -> None:

    if user.user_type != constants.CUSTOMER:
        raise exceptions.ForbiddenActionException("Only customers can like events")

    if react == constants.LIKE:
        like_event(event_id, user.user_id)

    elif react == constants.DISLIKE:
        dislike_event(event_id, user.user_id)

    else:
        unreact_event(event_id, user.user_id)
