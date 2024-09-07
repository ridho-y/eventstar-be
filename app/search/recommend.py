from sqlalchemy import desc
from .. import models, schemas, constants
from ..events import event_preview
from ..database import db
from .sort_filter import get_subset_results
from datetime import datetime
from difflib import SequenceMatcher


def get_generic_results(start: int, amount: int = constants.SEARCH_RESULTS) -> schemas.EventListingPreviewList:

    # Get all events ordered descending by liked omitting cancelled and past
    results = (
        db.get()
        .query(models.Event)
        .filter(models.Event.cancelled.is_(False))
        .filter(models.Event.end_time > datetime.now())
        .order_by(desc(models.Event.likes))
        .all()
    )

    # Get the required subset
    boundary_end = len(results)
    results = get_subset_results(results, start, boundary_end, amount)
    return schemas.EventListingPreviewList(eventListings=[event_preview.get_event_preview(event) for event in results])


def get_all_generic_events() -> schemas.EventListingPreviewList:
    results = (
        db.get()
        .query(models.Event.event_id.label("event_id"))
        .filter(models.Event.cancelled.is_(False))
        .filter(models.Event.end_time > datetime.now())
        .order_by(desc(models.Event.likes))
        .all()
    )

    return schemas.EventListingPreviewList(eventListings=[event_preview.get_event_preview(event) for event in results])


def get_all_tags() -> schemas.Tags:
    results = db.get().query(models.Tag.tag_name).order_by(models.Tag.tag_name).all()

    # Create a list to hold tag names
    tags_list = []

    for tag in results:
        tags_list.append(tag.tag_name)

    # Create a Tags object and set the tags field
    tags = schemas.Tags(tags=tags_list)

    return tags


def get_trending_generic_events():
    return get_generic_results(constants.START, constants.TRENDING)


def calculate_similarity_ratio(text1, text2):
    return SequenceMatcher(None, text1, text2).ratio()


def calculate_base_event_score(event, liked_events, followed_hosts):
    # Calculate the base event score
    score = 0
    if event.event_id in liked_events:
        score += constants.LIKE_WEIGHT
    if event.host_id in followed_hosts:
        score += constants.FOLLOW_WEIGHT
    score += event.likes * constants.POPULARITY_WEIGHT
    return score


def calculate_event_score(event, past_events, liked_events, followed_hosts):
    # Calculate similarity ratio between event title and description with past
    similarity_scores = []
    for past_event in past_events:
        title_similarity = calculate_similarity_ratio(event.title, past_event.title)
        description_similarity = calculate_similarity_ratio(event.description, past_event.description)
        similarity_score = max(title_similarity, description_similarity)
        similarity_scores.append(similarity_score)

    # Include highest of past booking similarities if they exist
    if len(similarity_scores) > 0:
        max_similarity = max(similarity_scores)
    else:
        max_similarity = 0

    score = calculate_base_event_score(event, liked_events, followed_hosts)

    # Check if the similarity ratio is above the threshold
    if max_similarity > constants.SIMILARITY_THRESHOLD:
        # If there is a similarity, give the event a higher score
        score += constants.HIGH_SCORE

    return score


def get_ordered_recommendations(user_id: int):
    # Get all the events a user has liked
    liked_events = db.get().query(models.Like.event_id).filter(models.Like.customer_id == user_id).all()
    liked_events = [item[0] for item in liked_events]

    # Get all the hosts a user is following
    followed_hosts = db.get().query(models.Follower.host_id).filter(models.Follower.customer_id == user_id).all()
    followed_hosts = [item[0] for item in followed_hosts]

    # Get all of a users past bookings
    past_events = (
        db.get()
        .query(models.Event)
        .join(models.Booking, models.Booking.event_id == models.Event.event_id)
        .filter(models.Booking.customer_id == user_id)
        .all()
    )

    # Get all of not past events
    all_events = (
        db.get()
        .query(models.Event)
        .filter(models.Event.event_id.notin_([event.event_id for event in past_events]))
        .all()
    )

    # Calculate the recommendation score for each event
    recommendation_scores = []

    for event in all_events:
        score = calculate_event_score(event, past_events, liked_events, followed_hosts)
        recommendation_scores.append({"event": event, "score": score})

    # Sort the events based on their scores
    recommended_events = sorted(recommendation_scores, key=lambda x: x["score"], reverse=True)
    # Get the recommended events
    return [item["event"] for item in recommended_events]


def get_recommended_events(user_id: int, start: int) -> schemas.EventListingPreviewList:
    # Get the required subset of recommended events
    recommended_events = get_ordered_recommendations(user_id=user_id)
    boundary_end = len(recommended_events)
    recommended_events = get_subset_results(recommended_events, start, boundary_end)

    return schemas.EventListingPreviewList(
        eventListings=[
            event_preview.get_event_preview(event)
            for event in recommended_events
        ]
    )


def get_all_recommended_events(user_id: int) -> schemas.EventListingPreviewList:
    recommended_events = get_ordered_recommendations(user_id=user_id)

    return schemas.EventListingPreviewList(
        eventListings=[
            event_preview.get_event_preview(event)
            for event in recommended_events
        ]
    )
