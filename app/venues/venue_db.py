from .. import models, schemas
from ..database import db
from .. import exceptions
from typing import List


# -------------------------------------------------------------------------------------- #
# ------------------------------  Create Venues ---------------------------------------- #


def create_base_venue(venue_info: schemas.Venue):
    new_venue = models.Venue(
        name=venue_info.name, location=venue_info.location, location_coords=venue_info.locationCoords
    )
    db.get().add(new_venue)
    db.get().flush()
    db.get().refresh(new_venue)

    return new_venue.venue_id


def create_venue_sections(venue_sections: List[schemas.VenueSection], venue_id: int):
    sections = [
        models.VenueSection(venue_id=venue_id, section_name=section.sectionName, total_seats=section.totalSeats)
        for section in venue_sections
    ]
    db.get().add_all(sections)
    db.get().flush()

    for section in sections:
        db.get().refresh(section)

    return sections


def create_venue_section_seats(venue_section: models.VenueSection):
    for seat_number in range(venue_section.total_seats):
        new_seat = models.VenueSeat(
            seat_name=venue_section.section_name + "-" + str(seat_number),
            seat_number=seat_number,
            section_id=venue_section.section_id,
        )
        db.get().add(new_seat)


# -------------------------------------------------------------------------------------- #
# ------------------------------  General Queries -------------------------------------- #


def get_venues():
    try:
        return db.get().query(models.Venue).all()
    except Exception:
        raise exceptions.BadGatewayException()


def get_venue_sections(venue_id: int) -> models.VenueSection:
    try:
        return db.get().query(models.VenueSection).filter(models.VenueSection.venue_id == venue_id).all()
    except Exception:
        raise exceptions.BadGatewayException()
