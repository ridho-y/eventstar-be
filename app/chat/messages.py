from .. import exceptions, constants, models, schemas
from ..constants import EventChatRequest, BroadcastType
from . import validators, message_db
from datetime import datetime
from sqlalchemy.orm import Session


def new_message(message: schemas.CreateChatMessage, session: Session):
    # Check that new message is valid
    error = validators.validate_new_message(message, session)
    if error:
        return error

    # Create and insert the new message

    new_message = models.ChatMessage(
        event_id=message.eventListingId,
        user_id=message_db.get_user_from_token(message.token, session).user_id,
        message=message.message,
        time_sent=datetime.now(),
        reply_to=message.replyMessageId if message.replyMessageId else None,
        files=message.files,
    )
    message_id = message_db.insert_message(new_message, session)
    return message_db.get_update_info(message, BroadcastType.POST.value, session, message_id).json()


def edit_message(message: schemas.CreateChatMessage, session: Session):
    # Check that edit message is valid
    error = validators.validate_modify_message(message, session)
    if error:
        return error

    # Check that new message is valid
    error = validators.validate_new_message(message, session)
    if error:
        return error

    message_db.edit_message(message, session)
    return message_db.get_update_info(message, BroadcastType.PUT.value, session).json()


def delete_message(message: schemas.CreateChatMessage, session: Session):
    # Check that delete message is valid
    error = validators.validate_modify_message(message, session)
    if error:
        return error
    message_db.delete_message(message, session)
    return message_db.get_update_info(message, BroadcastType.DELETE.value, session).json()


def like_message(message: schemas.CreateChatMessage, session: Session):
    # Check that like message is valid
    error = validators.validate_modify_message(message, session, like=True)
    if error:
        return error
    message_db.like_message(message, session)
    return message_db.get_update_info(message, BroadcastType.PUT.value, session).json()


def pin_message(message: schemas.CreateChatMessage, session: Session):
    # Check that pin message is valid
    error = validators.validate_pin_message(message, session)
    if error:
        return error
    message_db.pin_message(message, session)
    return message_db.get_update_info(message, BroadcastType.PUT.value, session).json()


def live_follower_count(host_id: int, session: Session):
    # Check that get follow count is valid
    error = validators.validate_follower_count(host_id, session)
    if error:
        return error
    return message_db.get_follower_count(host_id, session)


def update_chat(message: schemas.CreateChatMessage, session: Session):
    # Validate base message
    error = validators.validate_message(message, session)
    if error:
        return error

    if message.requestType == EventChatRequest.NEW.value:
        return new_message(message, session)
    elif message.requestType == EventChatRequest.EDIT.value:
        return edit_message(message, session)
    elif message.requestType == EventChatRequest.DELETE.value:
        return delete_message(message, session)
    elif message.requestType == EventChatRequest.LIKE.value:
        return like_message(message, session)
    elif message.requestType == EventChatRequest.PIN.value:
        return pin_message(message, session)


def get_messages(event_id: int, user: models.User, session: Session):
    error = validators.validate_get_message(event_id, user, session)
    if error:
        raise exceptions.InvalidInputException(error["error"])
    event = message_db.get_event(event_id, session)
    event_info = schemas.ChatEventInfo(
        eventListingId=event_id, hostId=event.host_id, thumbnail=event.thumbnail, title=event.title
    )
    # Get all messages in the chat
    messages = message_db.get_chat_messages(user.user_id, event_id, session)
    return schemas.ChatMessages(messages=messages, eventInfo=event_info)


def get_chats(user: models.User, session: Session):
    # Get host events or user booked events
    if user.user_type == constants.HOST:
        events = message_db.get_host_chats(user.user_id, session)
    else:
        events = message_db.get_user_chats(user.user_id, session)

    # Get chat info
    eventsList = message_db.get_chat_info([event[0] for event in events], session)
    return schemas.EventChat(eventChatPreviews=eventsList)
