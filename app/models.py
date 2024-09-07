from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index, Text, Numeric, TIMESTAMP, Date, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from .database import Base

"""
Notes: can use lazy='dynamic' set on relationships to allow for additional
filtering. 
"""

# ---------------------------------------------------------------------------------- #
# ---------------------------------- User Accounts --------------------------------- #


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    reset_code = Column(String(6), default=None)
    reset_password_timer = Column(TIMESTAMP, default=None)
    two_fa_code = Column(String(32), default=None)
    twofa_enabled = Column(Boolean, default=False)
    login_attempts = Column(Integer, default=0)
    user_type = Column(String(50))
    active = Column(Boolean, default=True)
    balance = Column(Numeric(10, 2), default=0)

    __table_args__ = (
        Index("unique_active_usernames", username, active, unique=True, postgresql_where=(~active)),
        Index("unique_active_emails", email, active, unique=True, postgresql_where=(~active)),
    )

    # relationships
    customer = relationship("Customer", uselist=False, post_update=True, back_populates="user")
    host = relationship("Host", uselist=False, post_update=True, back_populates="user")
    transactions = relationship("Transaction", lazy="dynamic")

    __mapper_args__ = {"polymorphic_on": user_type}


class Customer(User):
    __tablename__ = "customers"

    customer_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

    # relationships
    user = relationship("User", back_populates="customer")
    reviews = relationship("EventReview", back_populates="customer")
    followed_hosts = relationship("Follower", back_populates="customer", foreign_keys="[Follower.customer_id]")
    favourited_events = relationship("FavouritedEvent")
    bookings = relationship("Booking", back_populates="customer")

    __mapper_args__ = {"polymorphic_identity": "user"}


class Host(User):
    __tablename__ = "hosts"

    host_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    description = Column(Text, default="")
    org_name = Column(String(255), default="")
    org_email = Column(String(255), unique=True, default="")
    banner = Column(Text, default="")
    num_followers = Column(Integer, default=0)
    rating = Column(Numeric(10, 2), default=0)
    num_events = Column(Integer, default=0)

    # relationships
    user = relationship("User", back_populates="host")
    followers = relationship("Follower", back_populates="host", foreign_keys="[Follower.host_id]")
    events = relationship("Event", lazy="dynamic", back_populates="host")
    reviews = relationship("EventReview", back_populates="host")
    referrals = relationship("Referral", lazy="dynamic", back_populates="host")
    follower_logs = relationship("FollowerLog", lazy="dynamic", back_populates="host")
    event_sales_data = relationship("EventSales", lazy="dynamic", back_populates="host")
    daily_sales_data = relationship("HostDailySales", lazy="dynamic", back_populates="host")

    __mapper_args__ = {"polymorphic_identity": "host"}


class Follower(Base):
    __tablename__ = "followers"

    host_id = Column(Integer, ForeignKey("hosts.host_id"), primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), primary_key=True)

    # relationships
    host = relationship("Host", back_populates="followers")
    customer = relationship("Customer", back_populates="followed_hosts")


# ----------------------------------------------------------------------------------- #
# ----------------------------------- Venues ---------------------------------------- #


# Venues table
class Venue(Base):
    __tablename__ = "venues"

    venue_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    location_coords = Column(String, nullable=False)

    # Define relationships
    media = relationship("VenueMedia", lazy="dynamic")
    venue_sections = relationship("VenueSection", back_populates="venue")


# Venue sections table
class VenueSection(Base):
    __tablename__ = "venue_sections"

    section_id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"))
    section_name = Column(String(255))
    total_seats = Column(Integer, nullable=False)

    # Define relationships
    venue = relationship("Venue", uselist=False, back_populates="venue_sections")
    seats = relationship("VenueSeat")

    __table_args__ = (UniqueConstraint("venue_id", "section_name", name="unique_venue_section"),)


class VenueSeat(Base):
    __tablename__ = "venue_seats"

    seat_id = Column(Integer, primary_key=True)
    seat_name = Column(String(255))
    seat_number = Column(Integer)
    section_id = Column(Integer, ForeignKey("venue_sections.section_id"))


class VenueMedia(Base):
    __tablename__ = "venue_media"

    media_id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"))
    media_type = Column(String(255), nullable=False)
    media = Column(Text, nullable=False)


# ----------------------------------------------------------------------------------- #
# ----------------------------------- Events ---------------------------------------- #


class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("hosts.host_id"))
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    event_capacity = Column(Integer, nullable=False, default=0)
    minimum_cost = Column(Numeric(10, 2), default=0)
    event_type = Column(String(100), nullable=False)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    edited = Column(Boolean, default=False)
    cancelled = Column(Boolean, default=False)
    thumbnail = Column(Text)
    survey_made = Column(Boolean, default=False)

    # relationships
    host = relationship("Host", uselist=False, back_populates="events")
    event_media = relationship("EventMedia", lazy="dynamic", back_populates="event")
    faqs = relationship("Faq")
    tags = relationship("EventTag")
    reviews = relationship("EventReview", back_populates="event")
    announcements = relationship("EventAnnouncement")
    bookings = relationship("Booking", back_populates="event")

    online_event = relationship("OnlineEvent", uselist=False)
    seated_event = relationship("SeatedEvent", uselist=False)
    not_seated_event = relationship("NotSeatedEvent", uselist=False)

    reserves = relationship("EventReserve")


class OnlineEvent(Base):
    __tablename__ = "online_events"

    online_event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)
    online_link = Column(String(255))


class SeatedEvent(Base):
    __tablename__ = "seated_events"

    seated_event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"))

    # Relationships
    venue = relationship("Venue", uselist=False)


class NotSeatedEvent(Base):
    __tablename__ = "not_seated_events"

    not_seated_event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)
    location = Column(String(255), nullable=False)
    location_coords = Column(String, nullable=False)


# --------------------------------------------------------------------------------------- #
# ------------------------------ Events - Host Input ------------------------------------ #


class Faq(Base):
    __tablename__ = "faq"

    faq_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)


class EventMedia(Base):
    __tablename__ = "event_media"

    media_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    media_type = Column(String(255), nullable=False)
    media = Column(Text, nullable=False)

    event = relationship("Event", uselist=False, back_populates="event_media")


class EventAnnouncement(Base):
    __tablename__ = "event_announcements"

    announcement_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    event_host = Column(Integer, ForeignKey("hosts.host_id"))
    title = Column(String(255), nullable=False)
    date = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True)
    tag_name = Column(String(255), nullable=False, unique=True)

    events = relationship("EventTag", back_populates="tag")


class EventTag(Base):
    __tablename__ = "event_tags"

    event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.tag_id"), primary_key=True)
    event = relationship("Event", back_populates="tags")
    tag = relationship("Tag", uselist=False, back_populates="events")


# --------------------------------------------------------------------------------------- #
# ------------------------------ Events - User Input ------------------------------------ #


class Dislike(Base):
    __tablename__ = "dislikes"

    customer_id = Column(Integer, ForeignKey("customers.customer_id"), primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)


class Like(Base):
    __tablename__ = "likes"

    customer_id = Column(Integer, ForeignKey("customers.customer_id"), primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))


class EventReview(Base):
    __tablename__ = "event_reviews"

    review_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    event_id = Column(Integer, ForeignKey("events.event_id"))
    rating = Column(Integer, nullable=False)
    review = Column(Text, nullable=False)
    date = Column(Integer, nullable=False)
    edited = Column(Boolean, default=False)
    likes = Column(Integer, default=0)
    event_host = Column(Integer, ForeignKey("hosts.host_id"))
    host_replied = Column(Boolean, default=False)
    host_reply_date = Column(Integer)
    host_edited_reply = Column(Boolean, default=False)
    host_reply_message = Column(Text)

    # Relationships
    host = relationship("Host", uselist=False, back_populates="reviews")
    customer = relationship("Customer", uselist=False, back_populates="reviews")
    event = relationship("Event", uselist=False, back_populates="reviews")


class ReviewLikes(Base):
    __tablename__ = "review_likes"
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    review_id = Column(Integer, ForeignKey("event_reviews.review_id"))


# --------------------------------------------------------------------------------------- #
# --------------------------- Events - Pricing/Ticketing -------------------------------- #


class EventReserve(Base):
    __tablename__ = "event_reserves"

    event_reserve_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    reserve_name = Column(String(255), nullable=False)
    reserve_description = Column(Text)
    cost = Column(Numeric(10, 2), default=0)
    tickets_available = Column(Integer, nullable=False)

    # relationships
    sections = relationship("EventSection", back_populates="reserve")
    tickets = relationship("BookingReserve", back_populates="event_reserve")
    __table_args__ = (UniqueConstraint("event_id", "reserve_name", name="unique_event_reserve"),)


# Event sections table
class EventSection(Base):
    __tablename__ = "event_sections"

    event_section_id = Column(Integer, primary_key=True)
    event_reserve_id = Column(Integer, ForeignKey("event_reserves.event_reserve_id"))
    venue_section_id = Column(Integer, ForeignKey("venue_sections.section_id"))
    tickets_available = Column(Integer, nullable=False)

    venue_section = relationship("VenueSection", uselist=False)
    reserve = relationship("EventReserve", uselist=False, back_populates="sections")
    __table_args__ = (UniqueConstraint("event_section_id", "venue_section_id", name="unique_event_section"),)


# --------------------------------------------------------------------------------------- #
# ------------------------------------- Booking ----------------------------------------- #


# Bookings table
class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    date = Column(TIMESTAMP, nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    total_quantity = Column(Integer, nullable=False)
    referral_code = Column(String(255), ForeignKey("referrals.referral_code"), default="")
    amount_saved = Column(Numeric(10, 2), default=0)
    cancelled = Column(Boolean, default=False)

    # relationships
    event = relationship("Event", uselist=False, back_populates="bookings")
    customer = relationship("Customer", uselist=False, back_populates="bookings")
    booking_reserves = relationship("BookingReserve", back_populates="booking")
    referral = relationship("Referral", uselist=False, back_populates="bookings")


# Contains all tickets in a booking from the same reserve
class BookingReserve(Base):
    __tablename__ = "booking_reserve"

    booking_reserve_id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id"))
    reserve_id = Column(Integer, ForeignKey("event_reserves.event_reserve_id"))
    quantity = Column(Integer, default=0)

    booking = relationship("Booking", uselist=False, back_populates="booking_reserves")
    seats = relationship("SeatedTicket")
    event_reserve = relationship("EventReserve", uselist=False, back_populates="tickets")


class SeatedTicket(Base):
    __tablename__ = "seated_tickets"

    ticket_id = Column(Integer, primary_key=True)
    booking_reserve_id = Column(Integer, ForeignKey("booking_reserve.booking_reserve_id"), nullable=False)
    event_section_id = Column(Integer, ForeignKey("event_sections.event_section_id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("venue_seats.seat_id"))
    seat_name = Column(String(255), nullable=False)

    venue_seat = relationship("VenueSeat")


# ----------------------------------------------------------------------------------------- #
# ------------------------------------- Referrals ----------------------------------------- #


class Referral(Base):
    __tablename__ = "referrals"
    referral_code = Column(String(255), primary_key=True)
    host_id = Column(Integer, ForeignKey("hosts.host_id"))
    percentage_off = Column(Numeric(3, 2), nullable=False, default=0)
    referrer_cut = Column(Numeric(3, 2), nullable=False, default=0)
    referrer_name = Column(String(255), nullable=False)
    pay_id_phone = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0)
    amount_used = Column(Integer, default=0)

    host = relationship("Host", uselist=False, back_populates="referrals")
    bookings = relationship("Booking", back_populates="referral")


# ----------------------------------------------------------------------------------------- #
# ------------------------------------ User Profile --------------------------------------- #


class FavouritedEvent(Base):
    __tablename__ = "favourited_events"

    customer_id = Column(Integer, ForeignKey("customers.customer_id"), primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)

    event = relationship("Event")


class BillingInfo(Base):
    __tablename__ = "billing_info"

    billing_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    cardholder_name = Column(String(255), nullable=False)
    card_number = Column(String(255), nullable=False)
    expiry_month = Column(Integer, nullable=False)
    expiry_year = Column(Integer, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    country = Column(String(255), nullable=False)
    street_line1 = Column(String(255), nullable=False)
    street_line2 = Column(String(255), nullable=True)
    suburb = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    postcode = Column(Integer, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(255), nullable=False)

    user = relationship("User")


# ----------------------------------------------------------------------------------------- #
# ------------------------------------ Transactions --------------------------------------- #


class Transaction(Base):
    __tablename__ = "transaction"

    transaction_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    date = Column(TIMESTAMP, nullable=False)
    description = Column(Text, default="")
    credit = Column(Numeric(10, 2), default=0)
    debit = Column(Numeric(10, 2), default=0)
    balance = Column(Numeric(10, 2), default=0)


# --------------------------------------------------------------------------------------- #
# ------------------------------------ Event Chat --------------------------------------- #


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    message_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    message = Column(String, nullable=False)
    likes = Column(Integer, nullable=False, default=0)
    time_sent = Column(TIMESTAMP, nullable=False)
    reply_to = Column(Integer, ForeignKey("chat_messages.message_id"))
    edited = Column(Boolean, nullable=False, default=False)
    pinned = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, default=False)
    files = Column(ARRAY(String))

    event = relationship("Event")
    user = relationship("User")
    replies = relationship("ChatMessage", remote_side=[message_id])


class ChatLikes(Base):
    __tablename__ = "chat_likes"
    message_id = Column(Integer, ForeignKey("chat_messages.message_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

    message = relationship("ChatMessage")
    user = relationship("User")


# --------------------------------------------------------------------------------------- #
# --------------------------------------- SURVEY ---------------------------------------- #


class Survey(Base):
    __tablename__ = "survey"

    survey_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    host_id = Column(Integer, ForeignKey("hosts.host_id"))


class SurveyQuestion(Base):
    __tablename__ = "survey_question"

    survey_question_id = Column(Integer, primary_key=True)
    question = Column(String(255), default="")
    survey_id = Column(Integer, ForeignKey("survey.survey_id"))
    short_input = Column(Boolean)


class SurveyResponses(Base):
    __tablename__ = "survey_responses"

    customer_id = Column(Integer, ForeignKey("customers.customer_id"), primary_key=True)
    survey_id = Column(Integer, ForeignKey("survey.survey_id"), primary_key=True)


# --------------------------------------------------------------------------------------- #
# --------------------------- Analytics Data Collection  -------------------------------- #


class FollowerLog(Base):
    __tablename__ = "follower_log"

    host_id = Column(Integer, ForeignKey("hosts.host_id"), primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    follower_count = Column(Integer, default=0)

    host = relationship("Host", back_populates="follower_logs")


class EventSales(Base):
    __tablename__ = "event_sales"
    host_id = Column(Integer, ForeignKey("hosts.host_id"), primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    reserve_id = Column(Integer, ForeignKey("event_reserves.event_reserve_id"), primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    sales = Column(Integer, default=0)

    host = relationship("Host", uselist=False, back_populates="event_sales_data")


class HostDailySales(Base):
    __tablename__ = "host_daily_sales"
    host_id = Column(Integer, ForeignKey("hosts.host_id"), primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    sales = Column(Numeric(10, 2), default=0)

    host = relationship("Host", uselist=False, back_populates="daily_sales_data")
