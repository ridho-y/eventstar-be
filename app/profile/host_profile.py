import pydantic
from sqlalchemy import func, or_

from .. import models, schemas, exceptions, constants
from ..socials import socials_db, reviews_db
from ..events import event_preview
from ..auth import auth_db
from ..search import sort_filter


# ---------------------------------------------------------------------------------------------------- #
# ------------------------------  Host Public Profile Page Information ------------------------------- #


def get_host_public_profile_info(host_id: int, user: models.User = None) -> schemas.HostPublicProfileInformation:

    host = get_host(host_id)

    user_id = user.user_id if user else None
    reviews = [reviews_db.get_review_details_with_event_preview(review, user_id) for review in host.reviews]
    userInfo = None if not user else schemas.FollowsHost(followsHost=socials_db.user_follows_host(host.host_id, user.user_id))

    return schemas.HostPublicProfileInformation(
        reviews=reviews,
        userInfo=userInfo,
        orgName=host.org_name,
        description=host.description,
        orgEmail=host.org_email,
        banner=host.banner,
        noFollowers=host.num_followers,
        rating=host.rating,
        noEvents=host.num_events,
    )


def get_host(member_id: int) -> models.Host:
    base_user = auth_db.get_user_from_id(member_id)
    if base_user.user_type != constants.HOST or not base_user.host:
        raise exceptions.InvalidInputException(f"User with id {member_id} is not a host.")

    return base_user.host


# ---------------------------------------------------------------------------------------------------- #
# ---------------------------------------  Host Events  ---------------------------------------------- #


def get_past_host_events(host_id: int, sort: str = None) -> schemas.EventListingPreviewList:

    host = get_host(host_id)

    sort = sort_filter.get_event_sort(sort, original_titles=True)
    try:
        past_events = (
            host.events.filter(or_(models.Event.cancelled.is_(True), models.Event.end_time < func.now()))
            .order_by(sort)
            .all()
        )
        return schemas.EventListingPreviewList(
            eventListings=[event_preview.get_event_preview(event) for event in past_events]
        )

    except pydantic.error_wrappers.ValidationError:
        raise exceptions.InternalServerError("Host has missing fields.")


def get_ongoing_host_events(host_id: int, sort: str = None) -> schemas.EventListingPreviewList:

    host = get_host(host_id)

    sort = sort_filter.get_event_sort(sort, original_titles=True)

    try:
        ongoing_events = (
            host.events
            .filter(models.Event.cancelled.is_(False), models.Event.end_time >= func.now())
            .order_by(sort)
            .all()
        )
        return schemas.EventListingPreviewList(
            eventListings=[
                event_preview.get_event_preview(event)
                for event in ongoing_events
            ]
        )

    except pydantic.error_wrappers.ValidationError:
        raise exceptions.InternalServerError("Host has missing fields.")
