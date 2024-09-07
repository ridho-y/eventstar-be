from typing import Dict, List, Union
from .. import models, schemas
from ..database import db
from datetime import datetime
from sqlalchemy import union_all, or_
from ..constants import SortOption
from .recommend import get_ordered_recommendations

from .sort_filter import get_event_filters, get_event_sort, filter_distance, get_subset_results
from ..events import event_preview


def run_search_query(criteria: schemas.sortFilterEventListings, user_id: Union[int, None] = None):

    # Get the filter criteria for the search
    search_str = criteria.searchQuery
    filter_info = get_event_filters(criteria=criteria)
    filter_info["filters"].append(
        or_(
            models.Event.title.ilike(f"%{search_str}%"),
            models.Event.description.ilike(f"%{search_str}%")
        )
    )

    # Exclude cancelled and past events from the searc
    filter_info["filters"].append((models.Event.cancelled.is_(False)))
    filter_info["filters"].append((models.Event.end_time > datetime.now()))

    # Get all the types of events in the search
    online_events = event_preview.get_online_events_preview().filter(*filter_info["filters"])
    non_seated_events = event_preview.get_non_seated_events_preview().filter(*filter_info["filters"])
    seated_events = event_preview.get_seated_events_preview().filter(*filter_info["filters"])

    # Combine all types of events
    query = union_all(online_events, non_seated_events, seated_events)

    # Apply sorting based on criteria
    if criteria.sort:
        sort = get_event_sort(criteria.sort)
        if sort is not None:
            query = query.order_by(sort)

    results = db.get().execute(query).fetchall()

    # Add a location filter if specified for the search
    if "location_info" in filter_info.keys():
        results = filter_distance(results, location_info=filter_info["location_info"])

    boundary_end = len(results)
    subset_results = get_subset_results(results, criteria.start, boundary_end)
    # Sort by relevance if specified in the search
    if criteria.sort == SortOption.RELEVANCE.value and user_id:
        recommended_order = get_ordered_recommendations(user_id=user_id)
        new_order = [item.event_id for item in recommended_order]
        index_map = {value: index for index, value in enumerate(new_order)}
        subset_results = sorted(subset_results, key=lambda item: index_map.get(item.eventListingId, len(new_order)))

    return event_preview.parse_preview_output(custom_results=subset_results)
