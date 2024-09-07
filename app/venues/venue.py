from .. import models, schemas
from ..database import db
from .. import exceptions, constants
from . import venue_db
from typing import List


# -------------------------------------------------------------------------------------- #
# ---------------------------------  Venue Details ------------------------------------- #


def create_venue(venue_info: schemas.Venue):
    venue_id = venue_db.create_base_venue(venue_info)
    venue_sections = venue_db.create_venue_sections(venue_info.sections, venue_id)

    for section in venue_sections:
        venue_db.create_venue_section_seats(section)


# -------------------------------------------------------------------------------------- #
# ---------------------------------  Venue Details ------------------------------------- #


def get_all_venues() -> schemas.Venues:
    db_venues = venue_db.get_venues()
    venues = [
        schemas.Venue(name=venue.name, venueId=venue.venue_id, sections=get_venue_sections(venue.venue_id))
        for venue in db_venues
    ]

    return {"venues": venues}


# -------------------------------------------------------------------------------------- #
# --------------------------------  Venue Sections ------------------------------------- #


def get_venue_sections(venue_id: int) -> List[schemas.VenueSection]:
    db_venue_sections = venue_db.get_venue_sections(venue_id)
    return [
        schemas.VenueSection(sectionName=section.section_name, totalSeats=section.total_seats)
        for section in db_venue_sections
    ]
