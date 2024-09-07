from datetime import datetime
from .. import helpers, constants, exceptions
from ..booking import booking
from . import event_db


# -------------------------------------------------------------------------------------- #
# ---------------------------------  Delete Event -------------------------------------- #


def delete_event(event_id: int, user_id: int) -> None:
    event = event_db.get_event(event_id)
    if event.host_id != user_id:
        raise exceptions.ForbiddenAccessException("This user cannot delete this event.")

    if event.end_time < datetime.now():
        raise exceptions.ForbiddenActionException("Cannot cancel event. Event has already concluded.")

    if event.start_time < datetime.now():
        raise exceptions.ForbiddenActionException("Cannot cancel event. Event has already started.")

    # Make refunds
    for bookings in event.bookings:
        try:
            if not bookings.cancelled:
                booking.cancel_booking(bookings.booking_id, bookings.customer)
        except exceptions.InvalidInputException:
            raise exceptions.InvalidInputException(
                f"Cannot cancel event within {constants.BOOKING_CUTOFF_DAYS} days of event."
            )
        except Exception:
            pass

    email_list = event_db.get_event_customer_emails(event_id)
    try:
        if len(email_list) > 0:
            helpers.send_email_with_gmail(
                email_list, "Event has Been Cancelled", f"Event {event_id} has been cancelled"
            )
    except Exception:
        raise exceptions.BadGatewayException("Cannot send emails at the moment.")

    event.cancelled = True
