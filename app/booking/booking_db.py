from sqlalchemy import select

from .. import models, schemas
from ..database import db
from .. import exceptions
from typing import List


# --------------------------------------------------------------------------------------- #
# ------------------------------- Cancel Booking ---------------------------------------- #


def cancel_booking_reserve_seats(booking_reserve_id: int):
    try:
        (
            db.get()
            .query(models.SeatedTicket)
            .filter(models.SeatedTicket.booking_reserve_id == booking_reserve_id)
            .delete()
        )

    except Exception:
        raise exceptions.BadGatewayException()


def cancel_booking_reserves(booking_id: int):
    try:
        (
            db.get()
            .query(models.BookingReserve)
            .filter(models.BookingReserve.booking_id == booking_id)
            .delete()
        )

    except Exception:
        raise exceptions.BadGatewayException()


# --------------------------------------------------------------------------------------- #
# -------------------------------- Make Booking ----------------------------------------- #


def make_base_booking(base_info: schemas.MakeBaseBooking) -> int:
    try:
        new_base_booking = models.Booking(
            event_id=base_info.eventId,
            customer_id=base_info.userId,
            date=base_info.date,
            total_cost=base_info.totalCost,
            total_quantity=base_info.totalQuantity,
            referral_code=base_info.referralCode,
            amount_saved=base_info.amountSaved,
            cancelled=False,
        )
        db.get().add(new_base_booking)
        db.get().flush()
        db.get().refresh(new_base_booking)

    except Exception:
        raise exceptions.BadGatewayException()

    return new_base_booking.booking_id


def make_reserve_booking(booking_id: int, reserve_info: schemas.BookingReserves):
    try:
        new_reserve_booking = models.BookingReserve(
            booking_id=booking_id,
            reserve_id=reserve_info.reserve_id,
            quantity=reserve_info.quantity
        )
        db.get().add(new_reserve_booking)
        db.get().flush()
        db.get().refresh(new_reserve_booking)

    except Exception:
        raise exceptions.BadGatewayException()

    return new_reserve_booking.booking_reserve_id


def book_event_seat(seat: models.VenueSeat, booking_reserve_id: int, reserve_info: schemas.BookingReserves):
    try:
        seat_ticket = models.SeatedTicket(
            booking_reserve_id=booking_reserve_id,
            event_section_id=reserve_info.event_section_id,
            seat_id=seat.seat_id,
            seat_name=seat.seat_name,
        )
        db.get().add(seat_ticket)

    except Exception:
        raise exceptions.BadGatewayException()


# --------------------------------------------------------------------------------------- #
# -------------------------------- Booking info ----------------------------------------- #


def get_user_booking_ids(user_id: int, filters: List):
    try:
        booking_id_tuples = (
            db.get()
            .query(models.Booking.booking_id)
            .join(models.Event, models.Event.event_id == models.Booking.event_id)
            .filter(models.Booking.customer_id == user_id)
            .filter(*filters)
            .all()
        )
        return [booking_id_tuple[0] for booking_id_tuple in booking_id_tuples]
    except Exception:
        raise exceptions.BadGatewayException()


def get_booking(booking_id: int) -> models.Booking:
    try:
        return db.get().query(models.Booking).filter(models.Booking.booking_id == booking_id).one()
    except Exception:
        raise exceptions.NotFoundException(f"Unable to find booking with booking id '{booking_id}'.")


def get_first_available_seat(reserve_info: schemas.BookingReserves) -> models.VenueSeat:

    # get all seats in venue section
    all_seats = (
        db.get()
        .query(models.VenueSeat)
        .filter(models.VenueSeat.section_id == reserve_info.venue_section_id)
    )

    # get all seat tickets in current section
    booked_seats_subquery = (
        db.get()
        .query(models.SeatedTicket.seat_id)
        .filter(models.SeatedTicket.event_section_id == reserve_info.event_section_id)
        .subquery()
    )

    booked_seats = select(booked_seats_subquery.c.seat_id)

    available_seat = all_seats.filter(models.VenueSeat.seat_id.notin_(booked_seats)).first()

    if not available_seat:
        raise exceptions.InvalidInputException("Event section does not have any available seats.")

    return available_seat


def user_has_booked(user_id: int, event_id: int) -> bool:
    return (
        db.get()
        .query(models.Booking)
        .filter(models.Booking.customer_id == user_id)
        .filter(models.Booking.event_id == event_id)
        .filter(models.Booking.cancelled.is_(False))
        .first()
        is not None
    )
