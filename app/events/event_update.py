from .. import models, schemas
from ..database import db
from datetime import datetime
from .. import exceptions
from typing import List
from . import event_db


def update_media(event_id: int, media: List[str], event: models.Event, media_type: str):
    # First go through and delete everything in event media with this event_id
    (
        db.get()
        .query(models.EventMedia)
        .filter(models.EventMedia.event_id == event_id)
        .filter(models.EventMedia.media_type == media_type)
        .delete()
    )

    if media_type == "image":
        # Update thumbnail
        event.thumbnail = media[0]

    # Add each media
    for item in media:
        new_media = models.EventMedia(
            event_id=event_id,
            media_type=media_type,
            media=item
        )
        db.get().add(new_media)


def update_tags(event_id: int, tags: List[str]):
    # delete existing tags
    (
        db.get()
        .query(models.EventTag)
        .filter(models.EventTag.event_id == event_id)
        .delete()
    )

    for tag in tags:
        tag = event_db.get_or_create_tag(tag)
        event_tag = models.EventTag(event_id=event_id, tag_id=tag.tag_id)
        db.get().add(event_tag)


def update_faq(event_id: int, faqs: List[schemas.FAQModel]):
    # delete existing faq
    (
        db.get()
        .query(models.Faq)
        .filter(models.Faq.event_id == event_id)
        .delete()
    )
    for faq in faqs:
        if not faq.question or not faq.answer:
            raise exceptions.InvalidInputException("Faq cannot have an empty question or answer.")
        event_db.create_faq(faq, event_id)


def update_event(event_id: int, event_update: schemas.EventUpdate, user_id: int):
    event = event_db.get_event(event_id)

    if event.host_id != user_id:
        raise exceptions.ForbiddenAccessException("User is not allowed to edit event.")

    if event.start_time < datetime.now():
        raise exceptions.InvalidInputException("Host cannot edit an event that has already started!")

    if not event_db.is_event_editable(event.event_id):
        raise exceptions.ForbiddenAccessException("Cannot edit an event users have booked tickets to.")

    # Update the title
    if event_update.title:
        event.title = event_update.title

    # Update dates
    if event_update.startDateTime and event_update.endDateTime:
        if event_update.startDateTime >= event_update.endDateTime:
            raise exceptions.InvalidInputException("Start time must be before end time.")
        event.start_time = event_update.startDateTime
        event.end_time = event_update.endDateTime

    elif event_update.startDateTime:
        if event.end_time <= event_update.startDateTime:
            raise exceptions.InvalidInputException("Start time must be before end time.")
        event.start_time = event_update.startDateTime

    elif event_update.endDateTime:
        if event.start_time >= event_update.endDateTime:
            raise exceptions.InvalidInputException("Start time must be before end time.")
        event.end_time = event_update.endDateTime

    # Update summary
    if event_update.summary:
        event.summary = event_update.summary

    # Update description
    if event_update.description:
        event.description = event_update.description

    if event_update.images:
        if len(event_update.images) > 0:
            update_media(event_id=event_id, media=event_update.images, event=event, media_type="image")

    if event_update.tags:
        if len(event_update.tags) > 0:
            update_tags(event_id=event_id, tags=event_update.tags)

    if event_update.youtubeLinks:
        if len(event_update.youtubeLinks) > 0:
            update_media(event_id=event_id, media=event_update.youtubeLinks, event=event, media_type="youtube")

    if event_update.faq:
        if len(event_update.faq) > 0:
            update_faq(event_id=event_id, faqs=event_update.faq)
