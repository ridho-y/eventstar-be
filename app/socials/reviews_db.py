from datetime import datetime

from .. import exceptions, helpers, models, schemas, constants
from ..events import event_db, event_preview
from ..database import db
from ..booking import booking_db


# ------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------------  Make Reviews  ------------------------------------------------ #


def make_review(event_id: int, review_detail: schemas.Reviews, user: models.User) -> None:

    event = event_db.get_event(event_id)
    helpers.check_before_end_date(event.end_time)

    if user.user_type != constants.CUSTOMER:
        raise exceptions.ForbiddenActionException("Must be a registered customer to write a review.")

    if not booking_db.user_has_booked(user.user_id, event_id):
        raise exceptions.ForbiddenActionException("User must have a valid ticket to write a review.")

    if user_has_reviewed(user.user_id, event_id):
        raise exceptions.ForbiddenActionException("You have already submitted a review for this event.")

    helpers.verify_review_rating(review_detail.rating)

    user_review = models.EventReview(
        customer_id=user.user_id,
        event_id=event_id,
        rating=review_detail.rating,
        review=review_detail.review,
        date=datetime.now(),
        edited=False,
        likes=0,
        event_host=event.host_id,
        host_replied=False,
        host_reply_date=None,
        host_edited_reply=False,
        host_reply_message=None,
    )

    db.get().add(user_review)


def reply_to_review(review_id: int, response: schemas.HostRepliesReview, user: models.User) -> None:

    review = get_review(review_id)
    if review.host.host_id != user.user_id:
        raise exceptions.ForbiddenAccessException("User cannot reply to this review.")

    if review.host_replied:
        raise exceptions.InvalidInputException("You have already replied to this review.")

    review.host_replied = True
    review.host_reply_date = datetime.now()
    review.host_edited_reply = False
    review.host_reply_message = response.response


# ------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------------  Modify Reviews  ---------------------------------------------- #


def update_reviews(review_id: int, review_detail: schemas.UpdateReview, user: models.User) -> None:

    review = get_review(review_id)

    if user.user_type == constants.CUSTOMER:
        if review_detail.rating is not None:
            review.rating = review_detail.rating
        if review_detail.review is not None:
            review.review = review_detail.review
        review.date = datetime.now()

        review.date = datetime.now()
        review.edited = True

    elif user.user_type == constants.HOST:
        if review.host_replied:
            if review_detail.review is not None:
                review.host_reply_date = datetime.now()
                review.host_reply_message = review_detail.review
                review.host_edited_reply = True
                review.host_reply_date = datetime.now()

        else:
            review.host_replied = True
            review.host_reply_date = datetime.now()
            review.host_reply_message = review_detail.review

    else:
        raise exceptions.ForbiddenActionException(f"Unable to verify user type '{user.user_type}'.")


def like_reviews(review_id: int, user_id: int) -> None:

    # if user not yet like then can like
    # if user likes alr and press like again then unlike
    # review = db.get().query(models.EventReview).filter(models.EventReview.review_id == review_id).first()
    # review.likes += 1
    # db.get().add(review)
    # db.get().flush()

    # check if user like reviews
    user_liked = (
        db.get()
        .query(models.ReviewLikes)
        .filter(models.ReviewLikes.review_id == review_id)
        .filter(models.ReviewLikes.user_id == user_id)
        .first()
    )

    # if user likes it then
    if user_liked:
        (
            db.get()
            .query(models.ReviewLikes)
            .filter(models.ReviewLikes.review_id == review_id)
            .filter(models.ReviewLikes.user_id == user_id)
            .delete()
        )
        db.get().flush()

    else:
        db.get().add(models.ReviewLikes(user_id=user_id, review_id=review_id))
        db.get().flush()


def dislike_reviews(review_id: int) -> None:
    review = db.get().query(models.EventReview).filter(models.EventReview.review_id == review_id).first()
    review.likes -= 1
    db.get().add(review)


# ---------------------------------------------------------------------------------------------------------------- #
# -----------------------------------------  Get Review Information ---------------------------------------------- #


def get_review_details(review: models.EventReview, user_id: int) -> schemas.ReviewDetails:

    # Only users can like events
    is_user = db.get().query(models.Customer).filter(models.Customer.customer_id == user_id).first()
    user_liked_info = check_user_liked_reviews(user_id, review.review_id) if is_user else None

    return schemas.ReviewDetails(
        eventInfo=event_preview.get_event_preview(review.event),
        rating=review.rating,
        review=review.review,
        reviewId=review.review_id,
        eventListingId=review.event_id,
        hostId=review.event_host,
        orgName=review.host.org_name,
        firstName=review.customer.user.first_name,
        lastName=review.customer.user.last_name,
        memberId=review.customer.customer_id,
        date=review.date,
        edited=review.edited,
        likes=review.likes,
        host=get_host_review_reply(review.host, review.review_id, review.event_id),
        userInfo=user_liked_info,
    )


def get_event_reviews(eventListingId: int, user: models.User) -> schemas.AllReviewsWithDetail:

    all_reviews = (
        db.get()
        .query(models.EventReview)
        .filter(models.EventReview.event_id == eventListingId)
        .all()
    )
    return schemas.AllReviewsWithDetail(
        reviews=[
            get_review_details(review, user.user_id)
            for review in all_reviews
        ]
    )


def get_review_details_with_event_preview(review: models.EventReview, user_id: int) -> schemas.ReviewDetails:
    review_details = get_review_details(review, user_id)
    review_details.eventInfo = event_preview.get_event_preview(review.event)
    return review_details


def get_review(review_id: int) -> models.EventReview:
    try:
        return db.get().query(models.EventReview).filter(models.EventReview.review_id == review_id).one()

    except Exception:
        raise exceptions.InvalidInputException("Unable to find review.")


def get_host_review_reply(host: models.Host, review_id: int, event_id: int) -> schemas.HostReply:
    replies = (
        db.get()
        .query(models.EventReview)
        .filter(
            models.EventReview.event_host == host.host_id,
            models.EventReview.event_id == event_id,
            models.EventReview.review_id == review_id,
            models.EventReview.host_replied,
        )
        .first()
    )

    if replies is None:
        return None

    return schemas.HostReply(
        orgName=host.org_name,
        date=replies.host_reply_date,
        edited=replies.host_edited_reply,
        reply=replies.host_reply_message,
    )


def check_user_liked_reviews(user_id: int, review_id: int) -> schemas.UserInfo:
    user_liked = (
        db.get()
        .query(models.ReviewLikes)
        .filter(models.ReviewLikes.user_id == user_id)
        .filter(models.ReviewLikes.review_id == review_id)
        .first()
    ) is not None

    return schemas.UserInfo(userLiked=user_liked)


# ---------------------------------------------------------------------------------------------------------------- #
# -----------------------------------------  General Review Queries ---------------------------------------------- #


def user_has_reviewed(user_id: int, event_id: int) -> bool:
    return (
        db.get()
        .query(models.EventReview)
        .filter(models.EventReview.customer_id == user_id)
        .filter(models.EventReview.event_id == event_id)
        .first()
        is not None
    )
