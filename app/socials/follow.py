from datetime import date, timedelta
from sqlalchemy import asc
from .. import exceptions, models, schemas, constants
from ..database import db
from ..socials import socials_db
from ..auth import auth_db

# --------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Follow / Unfollow host ----------------------------------------------- #


def follow_unfollow_host(host_id: int, user: models.User) -> None:

    # Check that host is a host
    host = auth_db.get_user_from_id(host_id)
    if not host.user_type == constants.HOST:
        raise exceptions.ForbiddenAccessException("User to follow is not a host.")

    # Check that the user is a user
    if not user.user_type == constants.CUSTOMER:
        raise exceptions.ForbiddenAccessException("Only users can follow hosts.")

    if not socials_db.user_follows_host(host_id, user.user_id):
        follow_host(user.customer, host.host)
    else:
        unfollow_host(user.customer, host.host)


def follow_host(user: models.Customer, host: models.Host):
    user_follow = models.Follower(host_id=host.host_id, customer_id=user.customer_id)

    db.get().add(user_follow)
    db.get().commit()
    log_followers(host, 1)


def unfollow_host(user: models.Customer, host: models.Host):
    (
        db.get()
        .query(models.Follower)
        .filter(models.Follower.host_id == host.host_id)
        .filter(models.Follower.customer_id == user.customer_id)
        .delete()
    )
    db.get().commit()
    log_followers(host, -1)


# ------------------------------------------------------------------------------------------------------------- #
# -----------------------------------------  Log Follower data  ----------------------------------------------- #


def get_or_create_follower_log(host: models.Host):
    todays_log = (
        db.get()
        .query(models.FollowerLog)
        .filter(models.FollowerLog.host_id == host.host_id)
        .filter(models.FollowerLog.date == date.today())
        .first()
    )

    if todays_log:
        return todays_log

    todays_log = models.FollowerLog(
        host_id=host.host_id,
        date=date.today(),
        follower_count=host.num_followers
    )

    db.get().add(todays_log)
    return todays_log


def log_followers(host: models.Host, change: int):
    todays_log = get_or_create_follower_log(host)
    todays_log.follower_count = host.num_followers + change
    db.get().add(todays_log)


# ------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------------  Analytics  --------------------------------------------------- #


def get_host_followers_graph_data(user: models.User) -> schemas.GraphData:
    if not user.user_type == constants.HOST:
        raise exceptions.ForbiddenActionException("User cannot have any followers.")

    days: int = constants.SALES_DATA_LIMIT
    start_date = date.today() - timedelta(days=days)
    all_dates = {start_date + timedelta(days=i): 0 for i in range(days)}

    limit = date.today() - timedelta(days=constants.SALES_DATA_LIMIT)
    followers_data = (
        user.host.follower_logs
        .filter(models.FollowerLog.date >= limit)
        .order_by(asc(models.FollowerLog.date))
        .all()
    )

    for follower in followers_data:
        all_dates[follower.date] = follower.follower_count

    return schemas.GraphData(
        data=[
            schemas.DataPoint(xValue=date, yValue=followers)
            for date, followers in all_dates.items()
        ]
    )
