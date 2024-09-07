from .. import models, schemas
from typing import Dict, List, Optional
from jose import JWTError, jwt
from datetime import datetime
from sqlalchemy.orm import Session
from ..auth.authenticate import SECRET_KEY, ALGORITHM


def validate_user_booking(customer_id: int, event_id: int, session: Session):
    return (
        session.query(models.Booking)
        .filter(models.Booking.customer_id == customer_id)
        .filter(models.Booking.event_id == event_id)
        .filter(models.Booking.cancelled.is_(False))
        .first()
        is not None
    )


def validate_reply_message(message_id: int, event_id: int, session: Session):
    return (
        session.query(models.ChatMessage)
        .filter(models.ChatMessage.message_id == message_id)
        .filter(models.ChatMessage.event_id == event_id)
        .filter(models.ChatMessage.deleted.is_(False))
        .first()
        is not None
    )


def get_event(event_id: int, session: Session) -> models.Event:
    return session.query(models.Event).filter(models.Event.event_id == event_id).first()


def get_user(user_id: int, session: Session) -> models.User:
    return session.query(models.User).filter(models.User.user_id == user_id).first()


def get_message(message_id: int, session: Session) -> models.ChatMessage:
    return session.query(models.ChatMessage).filter(models.ChatMessage.message_id == message_id).first()


def get_liked_message(user_id: int, message_id: int, session: Session) -> Optional[models.ChatLikes]:
    return session.query(models.ChatLikes).filter_by(message_id=message_id, user_id=user_id).first()


def get_host_chats(user_id: int, session: Session):
    return session.query(models.Event.event_id).filter(models.Event.host_id == user_id).all()


def get_user_from_token(token: str, session: Session):
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
        user = get_user(token_data.memberId, session)
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


def get_user_chats(user_id: int, session: Session):
    return (
        session.query(models.Booking.event_id)
        .filter(models.Booking.customer_id == user_id)
        .filter(models.Booking.cancelled.is_(False))
        .all()
    )


def insert_message(message: models.ChatMessage, session: Session):
    session.add(message)
    session.commit()
    session.refresh(message)
    return message.message_id


def edit_message(message: schemas.CreateChatMessage, session: Session):
    old_message = get_message(message.messageId, session)
    old_message.message = message.message
    old_message.edited = True
    session.commit()
    session.refresh(old_message)


def pin_message(message: schemas.CreateChatMessage, session: Session):
    old_message = get_message(message.messageId, session)
    if old_message.pinned:
        old_message.pinned = False
    else:
        old_message.pinned = True
    session.commit()
    session.refresh(old_message)


def delete_message(message: schemas.CreateChatMessage, session: Session):
    old_message = get_message(message.messageId, session)
    old_message.message = "This message has been deleted"
    old_message.deleted = True
    old_message.files = []
    old_message.reply_to = None
    old_message.pinned = False
    old_message.edited = False
    session.commit()
    session.refresh(old_message)


def like_message(message: schemas.CreateChatMessage, session: Session):
    user_id = get_user_from_token(message.token, session).user_id
    existing_like = get_liked_message(user_id, message.messageId, session)
    if existing_like:
        session.delete(existing_like)
    else:
        new_like = models.ChatLikes(
            message_id=message.messageId,
            user_id=user_id
        )
        session.add(new_like)
    session.commit()


def get_follower_count(host_id: int, session: Session) -> int:
    host = session.query(models.Host).filter(models.Host.host_id == host_id).first()
    return host.num_followers


def get_update_info(message: schemas.CreateChatMessage, broadcast_type: str, session: Session, messageId: int = None) -> schemas.ChatMessage:
    
    text = get_message(messageId if messageId else message.messageId, session)
    text_message = schemas.Message(
        memberId=text.user_id,
        messageId=text.message_id,
        dateTime=text.time_sent,
        username=get_user(text.user_id, session).username,
        message=text.message,
        replyMessageId=text.reply_to,
        files=text.files,
        noLikes=text.likes,
        edited=text.edited,
        pinned=text.pinned,
        deleted=text.deleted,
    )
    return schemas.ChatMessage(type=broadcast_type, messageId=text.message_id, message=text_message)


def get_chat_messages(user_id: int, event_id: int, session: Session) -> Dict:
    messages = session.query(models.ChatMessage).filter(models.ChatMessage.event_id == event_id).all()
    message_dict = {}
    for message in messages:
        liked_status = schemas.Liked(liked=get_liked_message(user_id, message.message_id, session) is not None)
        message_info = schemas.MessageInfo(
            memberId=message.user_id,
            messageId=message.message_id,
            dateTime=message.time_sent,
            username=get_user(message.user_id, session).username,
            message=message.message,
            replyMessageId=message.reply_to,
            files=message.files,
            noLikes=message.likes,
            edited=message.edited,
            pinned=message.pinned,
            userInfo=liked_status,
            deleted=message.deleted,
        )
        message_dict[message.message_id] = message_info
    return message_dict


def get_chat_info(event_ids: List[int], session: Session) -> List[schemas.ChatEventInfo]:
    event_infos = []
    for event_id in event_ids:
        event = get_event(event_id, session)
        event_infos.append(
            schemas.ChatEventInfo(
                eventListingId=event_id,
                hostId=event.host_id,
                thumbnail=event.thumbnail,
                title=event.title
            )
        )
    return event_infos
