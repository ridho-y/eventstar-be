from .. import models, schemas
from .. import exceptions, constants
from . import event_db
from typing import List

# -------------------------------------------------------------------------------------- #
# ---------------------------------  Create Event -------------------------------------- #


def new_event(event_info: schemas.CreateEventListing, user: models.User):

    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenAccessException("User is not a host")

    if not event_db.check_host_info_set(user.user_id):
        raise exceptions.ForbiddenAccessException("Host information must be set prior to adding event")

    base_event = event_db.create_base_event(event_info, user.user_id)
    event_id = base_event.event_id

    # handle media: images - youtube links
    add_event_media(event_info, event_id)

    # handle tags
    add_event_tags(event_info.tags, event_id)

    # handle faq
    add_faqs(event_info.faq, event_id)

    # handle event_type and ticketing
    add_event_type_specifics(event_info, event_id)

    # calculate minimum_cost
    base_event.minimum_cost = calculate_minimum_cost(event_info)

    # calculate event_capacity
    base_event.event_capacity = event_db.calculate_tickets_available(event_id)

    return event_id


# --------------------------------------------------------------------------------------- #
# ------------------------------- Create Auxilliaries ----------------------------------- #


def add_event_media(event_info: schemas.EventListing, event_id: int):
    for image in event_info.images:
        event_db.create_event_media(image, "image", event_id)

    for youtube_link in event_info.youtubeLinks:
        event_db.create_event_media(youtube_link, "youtube", event_id)


def add_event_tags(tags: List[str], event_id: int):
    for tag in tags:
        event_db.create_event_tag(tag, event_id)


def add_faqs(faqs: List[schemas.FAQModel], event_id):
    for faq in faqs:
        if not faq.question or not faq.answer:
            raise exceptions.InvalidInputException("Faq cannot have an empty question or answer.")

        event_db.create_faq(faq, event_id)


def add_event_type_specifics(event_info: schemas.CreateEventListing, event_id: int):
    if event_info.type == constants.ONLINE and event_info.online:
        event_db.create_online_event(event_info.online, event_id)
        reserve = schemas.Reserve(
            name="GA", description="General Admission", cost=event_info.online.cost, quantity=event_info.online.quantity
        )

        add_non_seated_event_reserves([reserve], event_id)

    elif event_info.type == constants.INPERSON and event_info.inpersonNonSeated:
        event_db.create_in_person_event(event_info.inpersonNonSeated, event_id)
        add_non_seated_event_reserves(event_info.inpersonNonSeated.reserves, event_id)

    elif event_info.type == constants.SEATED and event_info.inpersonSeated:
        event_db.create_seated_event(event_info.inpersonSeated, event_id)
        add_seated_event_reserves(event_info.inpersonSeated.reserves, event_id, event_info.inpersonSeated.venueId)

    else:
        raise exceptions.InvalidInputException(
            "Event type does not exist or request does not provide matching event type information."
        )


# ---------------------------------------------------------------------------------------------------------------------------------- #
# -------------------------------------------- Create Event Payments/Ticketing ----------------------------------------------------- #


def add_non_seated_event_reserves(reserves: List[schemas.Reserve], event_id: int):
    if not reserves:
        raise exceptions.InvalidInputException("Event must have at least one reserve.")

    for reserve in reserves:
        event_db.create_event_reserve(reserve, event_id)


def add_seated_event_reserves(reserves: List[schemas.Reserve], event_id: int, venue_id: int):
    if not reserves:
        raise exceptions.InvalidInputException("Event must have at least one reserve.")

    for reserve in reserves:
        if not reserve.sections:
            raise exceptions.InvalidInputException(f"Reserve '{reserve.name}' must include at least one section.")

        reserve.quantity = event_db.calculate_seated_reserve_capacity(reserve.sections, event_id, venue_id)
        new_reserve_id = event_db.create_event_reserve(reserve, event_id)

        for venue_section in reserve.sections:
            event_db.create_event_section(venue_section, venue_id, new_reserve_id)


# ---------------------------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------------------------- Calculations ---------------------------------------------------------- #


def calculate_minimum_cost(event_info: schemas.EventListing) -> int:
    if event_info.type == constants.ONLINE:
        return event_info.online.cost

    elif event_info.type == constants.INPERSON:
        return min(reserve.cost for reserve in event_info.inpersonNonSeated.reserves)

    else:
        return min(reserve.cost for reserve in event_info.inpersonSeated.reserves)
