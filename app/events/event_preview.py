from typing import List
from sqlalchemy import select, distinct, func
from sqlalchemy.sql.expression import null

from .. import constants, models, schemas


# ---------------------------------------------------------------------------------------------------- #
# ---------------------------------------  Base Preview  --------------------------------------------- #


def get_event_preview(event: models.Event) -> schemas.EventListingPreview:

    return schemas.EventListingPreview(
        eventListingId=event.event_id,
        thumbnail=event.thumbnail,
        orgName="" if not event.host.org_name else event.host.org_name,
        noLikes=event.likes,
        noFollowers=event.host.num_followers,
        minimumCost=event.minimum_cost,
        location=get_event_location(event),
        hostId=event.host_id,
        title=event.title,
        startDateTime=event.start_time.isoformat(),
        endDateTime=event.end_time.isoformat(),
        type=event.event_type,
    )


def get_event_location(event: models.Event):
    if event.event_type == constants.SEATED:
        try:
            return event.seated_event.venue.name
        except Exception:
            pass

    elif event.event_type == constants.INPERSON:
        try:
            return event.not_seated_event.venue.name
        except Exception:
            pass

    return ""


# ---------------------------------------------------------------------------------------------------- #
# -------------------------------- Search - Preview With Metadata  ----------------------------------- #


def get_online_events_preview():
    preview_model = (
        select(
            distinct(models.Event.event_id).label("eventListingId"),
            models.Event.thumbnail.label("thumbnail"),
            models.Host.org_name.label("orgName"),
            models.Event.likes.label("noLikes"),
            models.Host.num_followers.label("noFollowers"),
            models.Event.minimum_cost.label("minimumCost"),
            models.Host.host_id.label("hostId"),
            models.Event.start_time.label("startDateTime"),
            models.Event.end_time.label("endDateTime"),
            models.Event.event_type.label("type"),
            null().label("location"),
            null().label("location_coords"),
            models.Event.title.label("title"),
        )
        .join(models.Host, models.Event.host_id == models.Host.host_id)
        .join(models.EventTag, models.Event.event_id == models.EventTag.event_id, isouter=True)
        .join(models.Tag, models.Tag.tag_id == models.EventTag.tag_id, isouter=True)
        .filter(func.lower(models.Event.event_type) == "online")
    )
    return preview_model


def get_non_seated_events_preview():
    preview_model = (
        select(
            distinct(models.Event.event_id).label("eventListingId"),
            models.Event.thumbnail.label("thumbnail"),
            models.Host.org_name.label("orgName"),
            models.Event.likes.label("noLikes"),
            models.Host.num_followers.label("noFollowers"),
            models.Event.minimum_cost.label("minimumCost"),
            models.Host.host_id.label("hostId"),
            models.Event.start_time.label("startDateTime"),
            models.Event.end_time.label("endDateTime"),
            models.Event.event_type.label("type"),
            models.NotSeatedEvent.location.label("location"),
            models.NotSeatedEvent.location_coords.label("location_coords"),
            models.Event.title.label("title"),
        )
        .join(models.Host, models.Event.host_id == models.Host.host_id)
        .join(models.NotSeatedEvent, models.Event.event_id == models.NotSeatedEvent.not_seated_event_id)
        .join(models.EventTag, models.Event.event_id == models.EventTag.event_id, isouter=True)
        .join(models.Tag, models.Tag.tag_id == models.EventTag.tag_id, isouter=True)
        .filter(models.Event.event_type == "inpersonNonSeated")
    )
    return preview_model


def get_seated_events_preview():
    preview_model = (
        select(
            distinct(models.Event.event_id).label("eventListingId"),
            models.Event.thumbnail.label("thumbnail"),
            models.Host.org_name.label("orgName"),
            models.Event.likes.label("noLikes"),
            models.Host.num_followers.label("noFollowers"),
            models.Event.minimum_cost.label("minimumCost"),
            models.Host.host_id.label("hostId"),
            models.Event.start_time.label("startDateTime"),
            models.Event.end_time.label("endDateTime"),
            models.Event.event_type.label("type"),
            models.Venue.location.label("location"),
            models.Venue.location_coords.label("location_coords"),
            models.Event.title.label("title"),
        )
        .join(models.Host, models.Event.host_id == models.Host.host_id)
        .join(models.SeatedEvent, models.Event.event_id == models.SeatedEvent.seated_event_id)
        .join(models.EventTag, models.Event.event_id == models.EventTag.event_id, isouter=True)
        .join(models.Tag, models.Tag.tag_id == models.EventTag.tag_id, isouter=True)
        .join(models.Venue, models.SeatedEvent.venue_id == models.Venue.venue_id)
        .filter(models.Event.event_type == "inpersonSeated")
    )
    return preview_model


def parse_preview_output(custom_results: List) -> schemas.EventListingPreviewList:
    results = [
        schemas.EventListingPreview(
            eventListingId=result.eventListingId,
            thumbnail=result.thumbnail,
            orgName=result.orgName,
            noLikes=result.noLikes,
            noFollowers=result.noFollowers,
            minimumCost=result.minimumCost,
            hostId=result.hostId,
            startDateTime=str(result.startDateTime),
            endDateTime=str(result.endDateTime),
            type=result.type,
            location=result.location,
            title=result.title,
        )
        for result in custom_results
    ]

    return schemas.EventListingPreviewList(eventListings=results)
