from .. import models, schemas
from .. import constants
from . import message_db
from sqlalchemy.orm import Session
from typing import Dict, Optional


def validate_message(message: schemas.CreateChatMessage, session: Session) -> Optional[Dict]:
    # Check that the user exists
    user = message_db.get_user_from_token(message.token, session)
    if user is None:
        return {"error": "User does not exist"}

    valid_usage = validate_get_message(message.eventListingId, user, session)
    # Check that the event exists
    if valid_usage:
        return valid_usage

    return None


def validate_new_message(message: schemas.CreateChatMessage, session: Session) -> Optional[Dict]:
    # Check if the reply message is set and that the replying message exists
    if message.replyMessageId and (
        not message_db.validate_reply_message(message.replyMessageId, message.eventListingId, session)
    ):
        return {"error": "The message to reply to does not exist"}

    # Check that the message length is valid
    if len(message.message) > constants.MAX_MESSAGE_LEN:
        return {"error": "Message length is too long"}

    return None


def validate_modify_message(
    mod_message: schemas.CreateChatMessage, session: Session, like: bool = False
) -> Optional[Dict]:
    # Check that editing message is the users message
    if not mod_message.messageId:
        return {"error": "No message id provided for editing message"}
    message = message_db.get_message(mod_message.messageId, session)
    if not message:
        return {"error": f"Message with id {mod_message.messageId} does not exist"}
    user = message_db.get_user_from_token(mod_message.token, session)
    if message.user_id != user.user_id and not like and user.user_type == constants.CUSTOMER:
        return {"error": "User can only edit or delete their own messages."}
    return None


def validate_pin_message(message: schemas.CreateChatMessage, session: Session) -> Optional[Dict]:
    # User must be the events host
    user = message_db.get_user_from_token(message.token, session)
    if user.user_type != constants.HOST:
        return {"error": "Only hosts can pin a message"}
    return None


def validate_follower_count(host_id: int, session: Session) -> Optional[Dict]:
    if not host_id:
        return {"error": "HostId is missing."}
    host = message_db.get_user(host_id, session)
    if host.user_type != constants.HOST:
        return {"error": "User is not a host"}
    return None


def validate_get_message(event_id: int, user: models.User, session: Session) -> Optional[Dict]:
    event = message_db.get_event(event_id, session)
    # Check that the event exists
    if not event:
        return {"error": f"Event with event id {event_id} does not exist"}

    # Check that the user has a booking or is the event host and is allowed to send messages
    if user.user_type == constants.HOST and event.host_id != user.user_id:
        return {"error": f"The host with id {user.user_id} is not the host for event with id {event.event_id}"}
    elif user.user_type == constants.CUSTOMER and not message_db.validate_user_booking(user.user_id, event_id, session):
        return {
            "error": f"The customer with id {user.user_id} does not have a booking for the event with id {event_id}"
        }
    return None
