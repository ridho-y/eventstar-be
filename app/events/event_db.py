from typing import List
from sqlalchemy import func, and_

from .. import constants, exceptions, models, schemas
from ..database import db


# --------------------------------------------------------------------------------------------- #
# -------------------------------------- Create Event ----------------------------------------- #


def create_base_event(event_info: schemas.CreateEventListing, host_id: int):
    base_event = models.Event(
        host_id=host_id,
        title=event_info.title,
        summary=event_info.summary,
        description=event_info.description,
        start_time=event_info.startDateTime,
        end_time=event_info.endDateTime,
        event_type=event_info.type,
        thumbnail=constants.DEFAULT_THUMBNAIL if not event_info.images else event_info.images[0],
    )

    db.get().add(base_event)
    db.get().flush()
    db.get().refresh(base_event)

    return base_event


def create_online_event(online_event_info: schemas.OnlineEventSpecifics, event_id: int):
    online_event = models.OnlineEvent(online_event_id=event_id, online_link=online_event_info.onlineLink)

    db.get().add(online_event)


def create_in_person_event(in_person_event_info: schemas.InPersonEventSpecifics, event_id: int):
    in_person_event = models.NotSeatedEvent(
        not_seated_event_id=event_id,
        location=in_person_event_info.location,
        location_coords=in_person_event_info.locationCoord,
    )

    db.get().add(in_person_event)


def create_seated_event(seated_event_info: schemas.SeatedEventSpecifics, event_id: int):
    seated_event = models.SeatedEvent(seated_event_id=event_id, venue_id=seated_event_info.venueId)

    db.get().add(seated_event)


# -------------------------------- Create Event Auxilliaries ------------------------------------- #


def create_event_media(media: str, media_type: str, event_id: int) -> int:
    new_media = models.EventMedia(event_id=event_id, media_type=media_type, media=media)
    db.get().add(new_media)
    db.get().flush()
    db.get().refresh(new_media)

    return new_media.media_id


def get_or_create_tag(tag_name: str):
    tag = db.get().query(models.Tag).filter(models.Tag.tag_name == tag_name).first()
    if not tag:
        tag = models.Tag(tag_name=tag_name)

    db.get().add(tag)
    db.get().flush()
    db.get().refresh(tag)
    return tag


def create_event_tag(tag_name: str, event_id: int):
    tag = get_or_create_tag(tag_name)
    event_tag = models.EventTag(
        event_id=event_id,
        tag_id=tag.tag_id
    )
    db.get().add(event_tag)


def create_faq(faq: schemas.FAQModel, event_id: int):
    new_faq = models.Faq(
        event_id=event_id,
        question=faq.question,
        answer=faq.answer
    )
    db.get().add(new_faq)


# ------------------------------- Create Event Payment/ticketing ----------------------------------- #


def create_event_reserve(reserve: schemas.Reserve, event_id):
    new_reserve = models.EventReserve(
        event_id=event_id,
        reserve_name=reserve.name,
        reserve_description=reserve.description,
        cost=reserve.cost,
        tickets_available=reserve.quantity,
    )
    db.get().add(new_reserve)
    db.get().flush()
    db.get().refresh(new_reserve)

    return new_reserve.event_reserve_id


def create_event_section(section_name: str, venue_id: int, event_reserve_id: int):
    venue_section = (
        db.get()
        .query(models.VenueSection)
        .filter(models.VenueSection.venue_id == venue_id)
        .filter(models.VenueSection.section_name == section_name)
        .first()
    )

    if not venue_section:
        raise exceptions.InvalidInputException(f"Selected venue does not contain section '{section_name}'")

    new_event_section = models.EventSection(
        event_reserve_id=event_reserve_id,
        venue_section=venue_section,
        tickets_available=venue_section.total_seats
    )
    db.get().add(new_event_section)


# ------------------------------- Calculate Event Information ----------------------------------- #


def calculate_tickets_available(event_id: int):
    return (
        db.get()
        .query(func.sum(models.EventReserve.tickets_available))
        .filter(models.EventReserve.event_id == event_id)
        .scalar()
    )


def calculate_seated_reserve_capacity(sections: List[str], event_id: int, venue_id: int):
    return sum(
        db.get()
        .query(models.VenueSection.total_seats)
        .filter(models.VenueSection.venue_id == venue_id)
        .filter(models.VenueSection.section_name == section)
        .scalar()
        for section in sections
    )


# ------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Event Getters ------------------------------------------ #


def get_event(event_id: int) -> models.Event:
    try:
        event = (
            db.get()
            .query(models.Event)
            .filter(models.Event.event_id == event_id)
            .one()
        )
    except Exception:
        raise exceptions.NotFoundException(f"Event '{event_id}' could not be found.")

    return event


def get_event_section_from_venue(event_reserve_id: int, venue_section_name: str) -> models.EventSection:
    try:
        return (
            db.get()
            .query(models.EventSection)
            .filter(models.EventSection.event_reserve_id == event_reserve_id)
            .join(models.EventSection.venue_section)
            .filter(models.VenueSection.section_name == venue_section_name)
            .one()
        )
    except Exception:
        raise exceptions.NotFoundException(f"Could not find venue section '{venue_section_name}'.")


def get_event_sections(event_id: int) -> List[models.EventSection]:
    try:
        return (
            db.get()
            .query(models.EventSection)
            .join(models.EventSection.reserve)
            .filter(models.EventReserve.event_id == event_id)
            .all()
        )
    except Exception:
        raise exceptions.BadGatewayException()


def get_event_reserve(reserve_name: str, event_id: int) -> models.EventReserve:
    try:
        return (
            db.get()
            .query(models.EventReserve)
            .filter(models.EventReserve.event_id == event_id)
            .filter(models.EventReserve.reserve_name == reserve_name)
            .first()
        )

    except Exception:
        raise exceptions.NotFoundException(f"Unable to find reserve '{reserve_name}' in event '{event_id}'.")


def get_event_reserves(event_id: int) -> List[models.EventReserve]:
    try:
        return (
            db.get()
            .query(models.EventReserve)
            .filter(models.EventReserve.event_id == event_id)
            .all()
        )

    except Exception:
        raise exceptions.BadGatewayException()


def get_event_end_time(event_id: int):
    result = (
        db.get()
        .query(models.Event.end_time)
        .filter(models.Event.event_id == event_id)
        .first()
    )
    return result[0] if result else None


# ------------------------------ Get Event Customer Information ----------------------------------- #


def get_event_customer_emails(event_id: int):
    customers = (
        db.get()
        .query(models.Booking.customer_id)
        .filter(and_(models.Booking.event_id == event_id, models.Booking.cancelled.is_(False)))
        .all()
    )
    if not customers:
        return []
    else:
        for customer in customers:
            emails = db.get().query(models.User.email).filter(models.User.user_id == customer.customer_id)
        return [customer.email for customer in emails]


# ------------------------------------------------------------------------------------------------- #
# ------------------------------------- General Event Queries ------------------------------------- #


def is_event_editable(event_id: int):
    return (
        db.get()
        .query(models.Booking)
        .filter(and_(models.Booking.event_id == event_id, models.Booking.cancelled.is_(False)))
        .first()
        is None
    )


def get_event_average_rating(event_id: int) -> float:
    ratings = db.get().query(models.EventReview).filter(models.EventReview.event_id == event_id).all()

    total_ratings = 0
    total_count = 0
    for rating in ratings:
        total_ratings = total_ratings + rating.rating
        total_count = total_count + 1

    if total_count == 0:
        return None

    return total_ratings / total_count


def commit_db():
    db.get().flush()


def check_host_info_set(host_id: int):
    host = db.get().query(models.Host).filter(models.Host.host_id == host_id).first()
    if not host or not host.description or not host.org_name or not host.org_email or not host.banner:
        return False
    return True


def get_event_likes_and_dislikes(event_id: int, user: models.User):
    event = get_event(event_id)
    if not event.host_id == user.user_id:
        raise exceptions.ForbiddenAccessException(
            f"User '{user.username}' does not have access to analytics for this event."
        )

    return schemas.LikesDislikes(
        likes=0 if not event.likes else event.likes,
        dislikes=0 if not event.dislikes else event.dislikes
    )

