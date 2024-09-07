from datetime import datetime, timedelta

from .. import models, schemas, constants, helpers
from ..events import event_preview, event_db
from .. import exceptions
from ..billing import transactions
from ..profile import host_analytics
from . import booking_db, referral
import locale

# ------------------------------------------------------------------------------------------- #
# -------------------------------  Event PreBooking Info ------------------------------------ #


def get_pre_booking_info(event_id: int) -> schemas.PreBookingInfo:
    event = event_db.get_event(event_id)

    pre_booking_info = schemas.PreBookingInfo(eventInfo=event_preview.get_event_preview(event))

    if event.event_type in (constants.ONLINE, constants.INPERSON):
        reserves_model = event_db.get_event_reserves(event_id)
        reserves_schema = [
            schemas.ReservePreBookingInfo(
                reserveName=reserve.reserve_name,
                ticketsLeft=reserve.tickets_available,
                cost=reserve.cost,
                description=reserve.reserve_description,
            )
            for reserve in reserves_model
        ]
        reserves = schemas.NonSeatedBookingInfo(reserves=reserves_schema)
        pre_booking_info.nonSeated = reserves

    elif event.event_type == constants.SEATED:
        sections_model = event_db.get_event_sections(event_id)
        sections_schema = [
            schemas.SectionPreBookingInfo(
                sectionName=section.venue_section.section_name,
                ticketsLeft=section.tickets_available,
                cost=section.reserve.cost,
                reserve=section.reserve.reserve_name,
                description=section.reserve.reserve_description,
            )
            for section in sections_model
        ]
        sections = schemas.SeatedBookingInfo(sections=sections_schema)
        pre_booking_info.seated = sections

    else:
        raise exceptions.BadGatewayException("Could not parse Event. Event data is corrupted.")

    return pre_booking_info


# --------------------------------------------------------------------------------------------- #
# ----------------------------------  Get Booking Details  ------------------------------------ #


def prep_filters(booking_filter: schemas.BookingFilter):
    filter_list = []
    if booking_filter.dateStart:
        dateStart = booking_filter.dateStart
        filter_list.append(models.Event.start_time >= dateStart)
    if booking_filter.searchstr:
        search = booking_filter.searchstr
        filter_list.append(models.Event.title.ilike(f"%{search}%"))
    return filter_list


def get_my_bookings(user: models.User, booking_filter: schemas.BookingFilter) -> schemas.Bookings:

    if not user.user_type == "user":
        raise exceptions.ForbiddenAccessException("Host cannot have bookings")

    booking_ids = booking_db.get_user_booking_ids(user.user_id, prep_filters(booking_filter))

    return schemas.Bookings(
        bookings=[
            get_booking_details(booking_id, user)
            for booking_id in booking_ids
        ]
    )


def get_booking_details(booking_id: int, user: models.User) -> schemas.Booking:
    booking = booking_db.get_booking(booking_id)

    if booking.customer_id != user.user_id:
        raise exceptions.ForbiddenAccessException("This user cannot view this booking.")

    reserves = [
        schemas.BookingReserveInfo(
            reserve=booking_reserve.event_reserve.reserve_name,
            tickets=booking_reserve.quantity,
            cost=booking_reserve.event_reserve.cost,
            description=booking_reserve.event_reserve.reserve_description,
            seats=[seat.seat_name for seat in booking_reserve.seats],
        )
        for booking_reserve in booking.booking_reserves
    ]

    percentage_off = 0 if not booking.referral else booking.referral.percentage_off

    return schemas.Booking(
        bookingId=booking.booking_id,
        cancelled=booking.cancelled,
        bookingDate=booking.date,
        eventId=booking.event_id,
        totalCost=booking.total_cost,
        totalQuantity=booking.total_quantity,
        referralCode=booking.referral_code,
        amountSaved=booking.amount_saved,
        percentageOff=percentage_off,
        reserves=reserves,
        eventInfo=event_preview.get_event_preview(booking.event),
    )


# ---------------------------------------------------------------------------------------- #
# ---------------------------------  Make Booking ---------------------------------------- #


def make_booking(booking_request: schemas.MakeBooking, user: models.User) -> schemas.BookingID:
    event_id = booking_request.eventListingId
    event = event_db.get_event(event_id)

    ######################## Handle Validations #######################
    if not event:
        raise exceptions.InvalidInputException("Event does not exist.")

    if event.cancelled:
        raise exceptions.InvalidInputException("Event has been cancelled.")

    if datetime.now() > event.start_time:
        raise exceptions.InvalidInputException("Unable to book. Event has already started.")

    total_cost = 0
    total_quantity = 0
    pending_reserves = []
    for reserve_info in booking_request.reserves:
        event_reserve = event_db.get_event_reserve(reserve_info.reserveName, event_id)
        pending_reserve = schemas.BookingReserves(
            reserveName=reserve_info.reserveName,
            quantity=reserve_info.quantity,
            section=reserve_info.section
        )

        if not event_reserve:
            raise exceptions.InvalidInputException(
                f"Event '{event.title}' does not have reserve '{reserve_info.reserveName}'."
            )

        if not event_reserve.tickets_available:
            raise exceptions.InvalidInputException(
                f"Could not book tickets. Reserve '{reserve_info.reserveName}' is sold out. {event_reserve.__dict__}"
            )

        if event_reserve.tickets_available < reserve_info.quantity:
            raise exceptions.InvalidInputException(
                f"Could not book {reserve_info.quantity} '{reserve_info.reserveName}' tickets. Reserve only has {event_reserve.tickets_available} remaining."
            )

        ############ If Seated Event #############
        if event.event_type == constants.SEATED:
            if not reserve_info.section:
                raise exceptions.InvalidInputException("Booking Section cannot be empty for seated events.")

            event_section = event_db.get_event_section_from_venue(event_reserve.event_reserve_id, reserve_info.section)

            if not event_section.tickets_available:
                raise exceptions.InvalidInputException(
                    f"Could not book tickets. Event Section '{reserve_info.section}' is sold out."
                )

            if event_section.tickets_available < reserve_info.quantity:
                raise exceptions.InvalidInputException(
                    f"Could not book {reserve_info.quantity} tickets in section {reserve_info.section}. Section only has {event_section.tickets_available} remaining."
                )

            ############ Cache Seated Event Results #############

            pending_reserve.event_section_id = event_section.event_section_id
            pending_reserve.venue_section_id = event_section.venue_section_id

        ############ Cache Reserve Results #############

        pending_reserve.reserve_id = event_reserve.event_reserve_id
        pending_reserve.cost = event_reserve.cost
        pending_reserves.append(pending_reserve)

        total_cost += event_reserve.cost * reserve_info.quantity
        total_quantity += reserve_info.quantity

    if total_quantity > 10:
        raise exceptions.InvalidInputException("User can only book a maximum of 10 tickets.")

    ####################### Calculate Discounts #########################

    actual_cost, host_amount_recieved = referral.apply_discount_and_referral_fee(
        booking_request.referralCode, total_cost
    )

    if actual_cost > user.balance:
        raise exceptions.InsuficientFundsException("User does not have enough funds.")

    ########################## Make booking #############################

    transactions.deduct_balance(float(actual_cost), "Booking deduction", event.title, user)
    transactions.add_balance(float(host_amount_recieved), "Booking deposit", event.title, event.host)

    base_booking_info = schemas.MakeBaseBooking(
        eventId=event_id,
        userId=user.user_id,
        date=datetime.now(),
        totalCost=actual_cost,
        totalQuantity=total_quantity,
        referralCode=booking_request.referralCode,
        amountSaved=(total_cost - actual_cost),
    )

    booking_id = booking_db.make_base_booking(base_booking_info)

    # handle booking reserves
    for reserve_info in pending_reserves:
        booking_reserve_id = booking_db.make_reserve_booking(booking_id, reserve_info)

        # log sales:
        host_analytics.log_event_reserve_sales(event_id, reserve_info.reserve_id, reserve_info.quantity, event.host_id)

        # make seated ticket reservations
        if event.event_type == constants.SEATED:
            for _ in range(reserve_info.quantity):
                seat = booking_db.get_first_available_seat(reserve_info)
                booking_db.book_event_seat(seat, booking_reserve_id, reserve_info)

    send_booking_confirmation(user.email, event, total_cost, total_quantity)

    return schemas.BookingID(bookingId=booking_id)


# --------------------------------------------------------------------------------------------- #
# ------------------------------------  Cancel Booking  --------------------------------------- #


def cancel_booking(booking_id: int, user: models.User, event_cancellation: bool = False) -> None:
    
    booking = booking_db.get_booking(booking_id)

    print(booking, booking.customer_id, booking.cancelled, booking.event_id)

    if booking.customer_id != user.user_id:
        raise exceptions.ForbiddenAccessException(f"User '{user.username}' does not have access to this booking.")

    if booking.cancelled:
        raise exceptions.InvalidInputException("Booking has already been cancelled.")

    if not event_cancellation:
        booking_cutoff = datetime.now() + timedelta(days=constants.BOOKING_CUTOFF_DAYS)
        if booking_cutoff > booking.event.start_time:
            raise exceptions.InvalidInputException(
                f"Cannot cancel booking within {constants.BOOKING_CUTOFF_DAYS} days of event."
            )

    # Delete seated tickets
    for booking_reserve in booking.booking_reserves:
        booking_db.cancel_booking_reserve_seats(booking_reserve.booking_reserve_id)
        host_analytics.log_event_reserve_sales(
            booking.event_id,
            booking_reserve.reserve_id,
            -booking_reserve.quantity,
            booking.event.host_id
        )

    # Delete booking reserves
    booking_db.cancel_booking_reserves(booking.booking_id)

    # Mark booking as cancelled:
    booking.cancelled = True

    # refund money
    host_amount_recieved = referral.refund_referral_fee(booking.referral, booking.total_cost)
    transactions.deduct_balance(float(host_amount_recieved), "Cancellation deduction", booking.event.title, booking.event.host)
    transactions.add_balance(float(booking.total_cost), "Cancellation refund", booking.event.title, user)

    send_booking_cancellation_email(booking, user)


# ---------------------------------------------------------------------------------------------------- #
# ---------------------------------  Booking Email notifications  ------------------------------------ #


def send_booking_confirmation(email: str, event: models.Event, total_cost: int, total_quantity: int) -> None:
    subject = "Eventstar Booking Confimation"
    body = f"""Booking confirmation for {event.title}.
    Booking Details:
    Total Cost: {locale.currency(total_cost, symbol=True, grouping=True)}.
    Total Tickets: {total_quantity}.
    Start time: {event.start_time}.
    """
    try:
        helpers.send_email_with_gmail([email], subject, body)
    except Exception:
        pass


def send_booking_cancellation_email(booking: models.Booking, user: models.User) -> None:
    subject = "Eventstar Booking Cancellation"
    body = f"""Booking Cancellation for {booking.event.title}.
    Booking Details:
    Total Cost: {locale.currency(booking.total_cost, symbol=True, grouping=True)}.
    Total Tickets: {booking.total_quantity}.
    """
    try:
        helpers.send_email_with_gmail([user.email], subject, body)
    except Exception:
        pass
