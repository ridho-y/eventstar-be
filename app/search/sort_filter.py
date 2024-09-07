from .. import models, schemas, constants
from datetime import datetime as datetimemod
import datetime
from typing import List
from sqlalchemy import or_, func, desc, asc
from sqlalchemy.sql import between
from ..exceptions import InvalidInputException
from ..constants import SortOption
import math


def convert_sort_criteria(sort_column):
    conversion = {"minimumCost": "minimum_cost", "noLikes": "likes", "startDateTime": "start_time"}
    return conversion[sort_column] if sort_column in conversion else sort_column


def get_subset_results(results: List, start: int, boundary_end: int, num: int = constants.SEARCH_RESULTS):
    # If end is less than start
    if boundary_end <= start:
        return []

    # Calculate the end position
    end = min(start + num, boundary_end)
    subset_results = results[start:end]
    return subset_results


def filter_distance(results, location_info):
    # Conver the coordinate format
    filter_distance = location_info["kmNearMe"]
    location = location_info["location"].strip("()")
    new_results = []
    latitude, longitude = location.split(",")

    # Convert the latitude and longitude to floats
    user_latitude = float(latitude.strip())
    user_longitude = float(longitude.strip())

    for result in results:
        coordinates = result.location_coords
        if coordinates:
            latitude, longitude = coordinates.strip("()").split(",")

            # Convert the latitude and longitude to floats
            latitude = float(latitude.strip())
            longitude = float(longitude.strip())

            # Use the haversine formula to calculate distance
            distance = (
                math.sqrt(
                    pow(math.radians(latitude - user_latitude), 2) + pow(math.radians(longitude - user_longitude), 2)
                )
                * 6371
            )

            # Only keep if within the filter distance
            if distance <= filter_distance:
                new_results.append(result)
    return new_results


def validate_sort(item):
    try:
        SortOption(item)
    except ValueError:
        raise InvalidInputException("Invalid sort criteria")


def get_event_filters(criteria: schemas.sortFilterEventListings) -> dict:
    filters = criteria.filter
    filter_criteria = {}
    filter_list = []

    if not filters:
        filter_criteria["filters"] = filter_list
        # If we want just everything in 50km
        if criteria.locationCoord:
            filter_criteria["location_info"] = {"location": criteria.locationCoord, "kmNearMe": 50}
        return filter_criteria

    # Date filters
    if filters.dateStart and filters.dateEnd:
        try:
            dateStart = datetimemod.strptime(filters.dateStart, "%Y-%m-%d").date()
            dateEnd = datetimemod.strptime(filters.dateEnd, "%Y-%m-%d").date()
        except Exception:
            raise InvalidInputException("Invalid datetime format")
        if dateStart > dateEnd:
            raise InvalidInputException("Start date must be before end date")
        if dateStart == dateEnd:
            dateStart = dateStart - datetime.timedelta(days=1)
            dateEnd = dateEnd + datetime.timedelta(days=1)
        filter_list.append(between(models.Event.start_time, dateStart, dateEnd))
    elif filters.dateStart:
        try:
            dateStart = datetimemod.strptime(filters.dateStart, "%Y-%m-%d").date()
        except Exception:
            raise InvalidInputException("Invalid datetime format")
        filter_list.append(models.Event.start_time >= dateStart)
    elif filters.dateEnd:
        try:
            dateEnd = datetimemod.strptime(filters.dateEnd, "%Y-%m-%d").date()
        except Exception:
            raise InvalidInputException("Invalid datetime format")
        filter_list.append(models.Event.start_time <= dateEnd)

    # Price filters
    if filters.priceStart and filters.priceEnd:
        if filters.priceStart > filters.priceEnd:
            raise InvalidInputException("Minimum price must be less than max price")
    if filters.priceStart:
        filter_list.append(models.Event.minimum_cost >= filters.priceStart)
    if filters.priceEnd:
        filter_list.append(models.Event.minimum_cost <= filters.priceEnd)

    # Type filter
    if filters.type:
        filter_list.append(func.lower(models.Event.event_type) == filters.type.lower())

    # Rating filter
    if filters.ratingAtLeast:
        filter_list.append(models.Host.rating >= filters.ratingAtLeast)

    # Tag filter
    if filters.tags is not None and len(filters.tags) > 0:
        or_conditions = [models.Tag.tag_name == tag for tag in filters.tags]
        filter_list.append(or_(*or_conditions))

    # Add specification for location filters
    if not criteria.locationCoord and filters.kmNearMe:
        raise InvalidInputException("Cannot retrieve your location to filter by km")

    if criteria.locationCoord and filters.kmNearMe:
        location = criteria.locationCoord
        filter_criteria["location_info"] = {"location": location, "kmNearMe": filters.kmNearMe}

    filter_criteria["filters"] = filter_list
    return filter_criteria


def get_event_sort(sort: str, original_titles: bool = False) -> dict:
    if not sort:
        return {"sort_column": "", "direction": ""}
    # Check that a valid sort option was provided
    validate_sort(sort)

    # Get associated column and direction for sort type
    sort_criteria = {
        SortOption.LOWEST_PRICE.value: ("minimumCost", "asc"),
        SortOption.HIGHEST_PRICE.value: ("minimumCost", "desc"),
        SortOption.ALPHABETICAL.value: ("title", "asc"),
        SortOption.ALPHABETICAL_REVERSE.value: ("title", "desc"),
        SortOption.MOST_LIKED.value: ("noLikes", "desc"),
        SortOption.UPCOMING.value: ("startDateTime", "asc"),
    }

    if sort in sort_criteria:
        sort_column, sort_direction = sort_criteria[sort]
        sort_column = convert_sort_criteria(sort_column) if original_titles else sort_column
        return asc(sort_column) if sort_direction == "asc" else desc(sort_column)
    else:
        return None
