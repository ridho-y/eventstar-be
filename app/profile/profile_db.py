from sqlalchemy import func

from .. import constants, exceptions, models, schemas
from ..database import db


# ---------------------------------------------------------------------------------------------------- #
# ------------------------------------  Profile Operations  ------------------------------------------ #


def update_profile(user: models.User, new_details: schemas.UpdateProfileDetails):

    if new_details.firstName:
        user.first_name = new_details.firstName
    if new_details.lastName:
        user.last_name = new_details.lastName
    if new_details.username:
        user.username = new_details.username
    if new_details.email:
        user.email = new_details.email

    if user.user_type == constants.HOST:
        if new_details.orgName == "" or new_details.orgName:
            user.host.org_name = new_details.orgName
        if new_details.orgName == "" or new_details.description:
            user.host.description = new_details.description
        if new_details.orgEmail == "" or new_details.orgEmail:
            user.host.org_email = new_details.orgEmail

        user.host.banner = constants.DEFAULT_BANNER if not new_details.banner else new_details.banner


def delete_profile(user: models.User):
    if user.user_type == constants.HOST:

        if user.host.events.filter(not models.Event.cancelled, models.Event.end_time >= func.now()):
            raise exceptions.InvalidInputException(
                f"Error: Cannot delete host '{user.username}'. Ongoing events must first be cancelled."
            )
        # Remove followers
        db.get().query(models.Follower).where(models.Follower.host_id == user.user_id).delete()

    elif user.user_type == constants.CUSTOMER:

        # Remove follows
        db.get().query(models.Follower).where(models.Follower.customer_id == user.user_id).delete()
        # Remove Like
        db.get().query(models.Like).where(models.Like.customer_id == user.user_id).delete()
        # Remove Dislike
        db.get().query(models.Dislike).where(models.Dislike.customer_id == user.user_id).delete()

    # For both
    user.first_name = constants.DELETED_USER
    user.last_name = constants.DELETED_USER
    user.username = constants.DELETED_USER
    user.email = constants.DELETED_USER_EMAIL
    user.password = constants.DELETED_USER
    user.active = False

    # Remove Billing Info
    db.get().query(models.BillingInfo).where(models.BillingInfo.user_id == user.user_id).delete()


# ---------------------------------------------------------------------------------------------------- #
# ----------------------------------  Get Profile Information ---------------------------------------- #


def get_host_personal_profile(user: models.User) -> schemas.ProfileInfo:
    profile = get_base_user_personal_profile(user)
    if user.host:
        profile.orgName = user.host.org_name
        profile.description = user.host.description
        profile.orgEmail = user.host.org_email
        profile.banner = user.host.banner
        profile.noFollowers = user.host.num_followers
        profile.rating = user.host.rating
        profile.noEvents = user.host.num_events

    return profile


def get_base_user_personal_profile(user: models.User) -> schemas.ProfileInfo:
    return schemas.ProfileInfo(
        memberId=user.user_id,
        isHost=user.host is not None,
        firstName=user.first_name,
        lastName=user.last_name,
        username=user.username,
        email=user.email,
        balance=user.balance,
    )


def get_profile(user: models.User) -> schemas.ProfileInfo:
    if user.host:
        return get_host_personal_profile(user)
    else:
        return get_base_user_personal_profile(user)


def get_following_hosts(user: models.User):
    # Ensure that the user is a host
    if user.user_type == constants.HOST:
        raise exceptions.InvalidInputException("Only users can follow hosts")

    # Fetch the hosts that the user is following
    followed_hosts = user.customer.followed_hosts

    # Add each followed host
    return schemas.FollowingHostProfileList(
        following=[
            schemas.FollowingHostProfile(hostId=host.host.host_id, orgName=host.host.org_name)
            for host in followed_hosts
        ]
    )


def get_host_org_name(event_id: int):
    event = db.get().query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise exceptions.InvalidInputException(f"No event found for id {event_id}")

    host = db.get().query(models.Host).filter(models.Host.host_id == event.host_id).first()
    if not host:
        raise exceptions.InvalidInputException(f"No host found for id {event.host_id}")

    # Extract and return org_name
    return host.org_name
