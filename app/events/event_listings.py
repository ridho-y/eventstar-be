from typing import List

from .. import constants, models, schemas, exceptions
from ..socials import socials_db, reviews_db
from ..booking import booking_db
from ..surveys import surveys_db
from . import event_db

# ---------------------------------------------------------------------------------------------------- #
# ------------------------------------  Event Listing Details  --------------------------------------- #


def get_event_listing_details(event_id: int, user: models.User = None) -> schemas.EventDetails:

    event = event_db.get_event(event_id)

    is_event_editable = event_db.is_event_editable(event_id)
    average_rating = event_db.get_event_average_rating(event_id)
    tags = [event_tag.tag.tag_name for event_tag in event.tags]
    images = [image.media for image in event.event_media.filter(models.EventMedia.media_type == constants.IMAGE)]
    youtube_links = [image.media for image in event.event_media.filter(models.EventMedia.media_type == constants.YOUTUBE)]
    faqs = get_event_FAQs(event)
    ticketsLeft = event_db.calculate_tickets_available(event_id)
    announcements = get_event_announcements(event)
    host_info = get_host_info(event.host)
    user_info = None if not user else get_user_event_interactions(event, user.user_id)

    response = schemas.EventDetails(
        title=event.title,
        startDateTime=event.start_time,
        endDateTime=event.end_time,
        type=event.event_type,
        editable=is_event_editable,
        averageRating=average_rating,
        cancelled=event.cancelled,
        eventListingId=event.event_id,
        memberId=event.host_id,
        summary=event.summary,
        description=event.description,
        tags=tags,
        images=images,
        youtubeLinks=youtube_links,
        faq=faqs,
        noLikes=event.likes,
        noDislikes=event.dislikes,
        minimumCost=event.minimum_cost,
        edited=event.edited,
        ticketsLeft=ticketsLeft,
        rating=event.host.rating,
        announcements=announcements,
        hostInfo=host_info,
        userInfo=user_info,
        online=get_online_event_details(event),
        inpersonNonSeated=get_non_seated_event_details(event),
        inpersonSeated=get_seated_event_details(event),
        surveyMade=surveys_db.get_made_survey_bool(event.event_id),
    )

    return response


# ---------------------------------------------------------------------------------------------------- #
# ---------------------------------------------  Helpers  -------------------------------------------- #


def get_event_FAQs(event: models.Event) -> List[schemas.FAQModel]:
    return [schemas.FAQModel(question=faq.question, answer=faq.answer) for faq in event.faqs]


def get_event_announcements(event: models.Event) -> List[schemas.Announcements]:
    return [
        schemas.Announcements(
            title=annoucement.title,
            date=annoucement.date.isoformat(),
            message=annoucement.message
        )
        for annoucement in event.announcements
    ]


# ---------------------------------------------------------------------------------------------------- #
# -----------------------------------  Event Type Helpers  ------------------------------------------- #


def get_online_event_details(event: models.Event) -> schemas.OnlineEventSpecifics:
    if not event or not event.online_event:
        return None

    try:
        online_reserve = event.reserves[0]
    except Exception:
        raise exceptions.InternalServerError(f"Unable to read event reserves. Event info for {event.title} is corrupted.")

    online_schema = schemas.OnlineEventSpecifics(
        onlineLink=event.online_event.online_link,
        cost=online_reserve.cost,
        tickets=online_reserve.tickets_available
    )

    return online_schema


def get_seated_event_details(event: models.Event) -> schemas.SeatedEventSpecifics:
    if not event or not event.seated_event:
        return None

    return schemas.SeatedEventSpecifics(
        venueId=event.seated_event.venue_id,
        venue=event.seated_event.venue.name,
        reserves=get_reserve_info(event)
    )


def get_non_seated_event_details(event: models.Event) -> schemas.InPersonEventSpecifics:
    if not event or not event.not_seated_event:
        return None

    return schemas.InPersonEventSpecifics(
        location=event.not_seated_event.location,
        locationCoord=event.not_seated_event.location_coords,
        reserves=get_reserve_info(event),
    )


def get_reserve_info(event: models.Event) -> List[schemas.EventReserve]:
    return [
        schemas.EventReserve(
            name=reserve.reserve_name,
            description=reserve.reserve_description,
            cost=reserve.cost,
            tickets=reserve.tickets_available,
            sections=[section.venue_section.section_name for section in reserve.sections],
        )
        for reserve in event.reserves
    ]


# ---------------------------------------------------------------------------------------------------- #
# ---------------------------------  Event User/Host Info  ------------------------------------------- #


def get_user_event_interactions(event: models.Event, user_id: int) -> schemas.UserInfoEventListing:

    reaction = socials_db.get_user_event_reaction(event.event_id, user_id)
    favourite = socials_db.is_event_favourited(event.event_id, user_id)
    follows_host = socials_db.user_follows_host(event.host_id, user_id)
    bought_ticket = booking_db.user_has_booked(user_id, event.event_id)
    has_reviewed = reviews_db.user_has_reviewed(user_id, event.event_id)

    # reaction, favourited, followsHost, boughtTicket, hasReviewed
    return schemas.UserInfoEventListing(
        reaction=reaction,
        favourited=favourite,
        followsHost=follows_host,
        boughtTicket=bought_ticket,
        hasReviewed=has_reviewed,
    )


def get_host_info(host: models.Host) -> schemas.HostInformation:
    if not host:
        return None

    return schemas.HostInformation(
        orgName=host.org_name,
        description=host.description,
        orgEmail=host.org_email,
        banner=host.banner,
        noFollowers=host.num_followers,
        rating=host.rating,
        noEvents=host.num_events,
    )
