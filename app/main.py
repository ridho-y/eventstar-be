import argparse
import json
from typing import Union, Dict
import uvicorn
from app.database import engine, get_db, db, SessionLocal
import os

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
    Request,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm


from . import constants, models, schemas
from .auth import auth_db, authenticate, twofa, validations
from .auth.authenticate import get_current_user, get_user_or_none
from .billing import billing, transactions
from .booking import booking, referral
from .profile import host_profile, profile_db, host_analytics
from .search import recommend, search
from .socials import favourites, follow, reviews_db, socials_db
from .venues import venue
from .chat import messages
from .events import event_db, create_event, delete_event, event_listings, event_update
from .surveys import create_surveys, delete_surveys, get_surveys, submit_surveys
from .exceptions import (
    BadGatewayException,
    ForbiddenAccessException,
    ForbiddenActionException,
    InsuficientFundsException,
    InvalidInputException,
    InvalidRequestException,
    NotFoundException,
    NotUniqueException,
    InternalServerError,
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configure CORS
origins = [os.environ.get("FRONTEND_URL"), "http://localhost:3000"]  # Replace with your frontend origin

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
with get_db() as session:
    db.set(session)
"""


@app.middleware("http")
async def attach_db_session_to_context_var(request: Request, call_next):
    with get_db() as session:
        db.set(session)
        response = await call_next(request)
        if response.status_code >= 400:
            session.rollback()
        else:
            session.commit()
        return response


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, id: int):
        await websocket.accept()
        self.active_connections[websocket] = id

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket)

    async def broadcast(self, message: str, id: int):
        for connection, identifier in self.active_connections.items():
            if identifier == id:
                await connection.send_text(message)


manager = ConnectionManager()
count_manager = ConnectionManager()


# ----------------------------------------------------------------------------------------------------------- #
# ------------------------------------------- Authentication ------------------------------------------------ #
# ----------------------------------------------------------------------------------------------------------- #


@app.post("/auth/signup", response_model=None)
def user_signup(signup: schemas.SignUpRequest):
    try:
        validations.validate_email(signup.email)
        validations.validate_username(signup.username)
        validations.validate_password(signup.username, signup.password)
        validations.validate_member_type(signup.memberType)

    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except NotUniqueException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    auth_db.register_user(signup)

    return {}


@app.post("/auth/login", response_model=dict)
def login_for_access_token(login_request: OAuth2PasswordRequestForm = Depends()):
    emailOrUsername = login_request.username
    user = authenticate.authenticate_user(emailOrUsername, login_request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.twofa_enabled:
        if not login_request.client_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="2FA token required.")
        elif not twofa.verify_otp(user, login_request.client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect two factor authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    access_token = authenticate.create_access_token(data={"member_id": user.user_id, "member_type": user.user_type})
    return {"access_token": access_token}


@app.get("/auth/2fa/link", response_model=schemas.TwoFa)
def twofa_link(user: models.User = Depends(get_current_user)):
    try:
        code = twofa.enable_2fa(user)
    except InvalidRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    return schemas.TwoFa(code=code)


@app.get("/auth/2fa/check", response_model=schemas.Confirmation)
def twofa_check(user: models.User = Depends(get_current_user)):
    return schemas.Confirmation(value=user.twofa_enabled)


@app.put("/auth/2fa/disable", response_model=None)
def twofa_disable(user: models.User = Depends(get_current_user)):
    try:
        twofa.disable_2fa(user)
    except InvalidRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    return {}


# ------------------------------------------------------------------------------------------------------------- #
# ------------------------------------ Authentication - Reset Password ---------------------------------------- #
# ------------------------------------------------------------------------------------------------------------- #


@app.post("/auth/reset/email", response_model=None)
def send_reset_code_to_email(email: schemas.ResetEmail):
    try:
        authenticate.send_reset_code_to_email(email)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception:
        pass

    return {}


@app.post("/auth/reset/password/loggedOut", response_model=None)
def reset_password_loggedOut(reset: schemas.ResetPasswordAndCode):
    try:
        user = auth_db.get_user_by_reset_code(reset.code)
        if not authenticate.check_reset_code(user, reset.code):
            raise ForbiddenAccessException("Invalid Code or Code has expired.")
        auth_db.update_password(user, reset.new_password)
        auth_db.clear_reset_code(user)
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to validate code")

    return {}


@app.post("/auth/reset/password/loggedIn", response_model=None)
def update_password_loggedIn(update_pass: schemas.UpdatePass, user: models.User = Depends(get_current_user)):
    try:
        if not authenticate.verify_password(update_pass.old_password, user.password):
            raise HTTPException(status_code=403, detail="Incorrect Password.")
        auth_db.update_password(user, update_pass.new_password)
    except Exception as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


# ------------------------------------------------------------------------------------------------------------- #
# ----------------------------------------------- Profile ----------------------------------------------------- #
# ------------------------------------------------------------------------------------------------------------- #


@app.get("/profile", response_model=schemas.ProfileInfo)
def get_profile_details(user: models.User = Depends(get_current_user)):
    try:
        return profile_db.get_profile(user)
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.post("/profile", response_model=None)
def update_profile_details(new_details: schemas.UpdateProfileDetails, user: models.User = Depends(get_current_user)):
    try:
        if new_details.email and new_details.email != user.email:
            validations.validate_email(new_details.email)
        if new_details.username and new_details.username != user.username:
            validations.validate_username(new_details.username)
        profile_db.update_profile(user, new_details)

    except (InvalidInputException, NotUniqueException, NotFoundException) as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.delete("/profile", response_model=None)
def delete_profile(user: models.User = Depends(get_current_user)):
    try:
        profile_db.delete_profile(user)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.get("/profile/info", response_model=schemas.ShortProfileInfo)
def get_profile_info(user: models.User = Depends(get_current_user)):
    return schemas.ShortProfileInfo(
        firstName=user.first_name, isHost=(user.user_type == constants.HOST), memberId=user.user_id
    )


@app.get("/profile/following", response_model=schemas.FollowingHostProfileList)
def get_followed_hosts(user: models.User = Depends(get_current_user)):
    try:
        return profile_db.get_following_hosts(user)
    except (InvalidInputException, NotUniqueException) as e:
        raise HTTPException(status_code=400, detail=e.message)


@app.get("/profile/favourites", response_model=schemas.EventListingPreviewList)
def get_favourites(user: models.User = Depends(get_current_user)):
    try:
        return favourites.get_user_favourites(user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


# ------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------ Host Profile ----------------------------------------------------- #
# ------------------------------------------------------------------------------------------------------------- #


@app.get("/host/{memberId}", response_model=schemas.HostPublicProfileInformation)
def get_host_public_profile(memberId: int, user: models.User = Depends(get_user_or_none)):
    try:
        host_info = host_profile.get_host_public_profile_info(memberId, user)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    return host_info


@app.post("/host/pastEvents/{host_id}", response_model=schemas.EventListingPreviewList)
def get_past_host_events(host_id: int, sort: schemas.SortEventListings):
    try:
        return host_profile.get_past_host_events(host_id, sort.sort)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InternalServerError as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.post("/host/currEvents/{host_id}", response_model=schemas.EventListingPreviewList)
def get_current_host_events(host_id: int, sort: schemas.SortEventListings):
    try:
        return host_profile.get_ongoing_host_events(host_id, sort.sort)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InternalServerError as e:
        raise HTTPException(status_code=e.code, detail=e.message)


# ---------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------- Profile - Billing -------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


@app.post("/profile/billingInformation", response_model=None)
def add_billing(billingInfo: schemas.BillingInfo, user: models.User = Depends(get_current_user)):
    try:
        billing.insert_billing(user, billingInfo)
    except NotUniqueException as e:
        raise HTTPException(status_code=403, detail=e.message)
    return {}


@app.put("/profile/billingInformation/{billingId}", response_model=None)
def update_billing(
    billingId: int, billingInfo: schemas.UpdateBillingInfo, user: models.User = Depends(get_current_user)
):
    try:
        billing.update_billing(user, billingId, billingInfo)
    except InvalidInputException as e:
        raise HTTPException(status_code=403, detail=e.message)
    return {}


@app.get("/profile/billingInformation", response_model=schemas.AllBillingInfo)
def get_all_billings(user: models.User = Depends(get_current_user)):
    try:
        return billing.get_all_billings(user)
    except InvalidInputException as e:
        raise HTTPException(status_code=403, detail=e.message)


@app.get("/profile/billingInformation/{billingId}", response_model=schemas.BillingInfo)
def get_billing(billingId: int, user: models.User = Depends(get_current_user)):
    try:
        return billing.get_billing_schema(user, billingId)
    except InvalidInputException as e:
        raise HTTPException(status_code=403, detail=e.message)


@app.delete("/profile/billingInformation/{billingId}", response_model=None)
def delete_billing(billingId: int, user: models.User = Depends(get_current_user)):
    try:
        return billing.delete_billing(user, billingId)
    except InvalidInputException as e:
        raise HTTPException(status_code=403, detail=e.message)
    return {}


# ---------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------- Profile - Balance -------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


@app.put("/profile/balance", response_model=None)
def deposit_balance(balance_info: schemas.UpdateBalance, user: models.User = Depends(get_current_user)):
    try:
        transactions.deposit_balance(balance_info, user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.post("/profile/balance", response_model=None)
def withdraw_balance(balance_info: schemas.UpdateBalance, user: models.User = Depends(get_current_user)):
    try:
        transactions.withdraw_balance(balance_info, user)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


# ---------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Profile - Transactions ------------------------------------------------ #
# ---------------------------------------------------------------------------------------------------------------- #


@app.put("/profile/transactions", response_model=schemas.Transactions)
def get_my_transactions(start: schemas.Start, user: models.User = Depends(get_current_user)):
    try:
        return transactions.get_my_transactions(start.start, user)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


# ---------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------------- Event Listings -------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


@app.post("/eventListing", response_model=schemas.EventId)
def create_new_event(event_details: schemas.CreateEventListing, user: models.User = Depends(get_current_user)):
    try:
        new_event_id = create_event.new_event(event_details, user)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return schemas.EventId(eventListingId=new_event_id)


@app.put("/eventListing/{event_id}", response_model=None)
def update_event(event_id: int, updated_event: schemas.EventUpdate, user: models.User = Depends(get_current_user)):
    try:
        updated_event = event_update.update_event(event_id, updated_event, user.user_id)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.get("/eventListing/{event_id}", response_model=schemas.EventDetails)
def get_event_listing(event_id: int, user: models.User = Depends(get_user_or_none)):
    try:
        event_details = event_listings.get_event_listing_details(event_id, user)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return event_details


@app.delete("/eventListing/{event_id}", response_model=None)
def delete_event_listing(event_id: int, user: models.User = Depends(get_current_user)):
    try:
        delete_event.delete_event(event_id, user.user_id)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception:
        raise HTTPException(status_code=404, detail="Event not found")


@app.get("/eventListing/{event_id}/userInfo", response_model=schemas.UserInfoEventListing)
def get_event_user_info(event_id: int, user: models.User = Depends(get_user_or_none)):
    try:
        event_user_info = profile_db.get_user_event_interactions(event_id, user.user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")

    return event_user_info


@app.post("/eventListing/announcement")
def send_announcements(announcement: schemas.Announcements, user: models.User = Depends(get_current_user)):
    try:
        socials_db.make_announcement(announcement, user)
    except Exception as e:
        raise HTTPException(status_code=e.code, detail=e.message)


# ---------------------------------------------------------------------------------------------------------------- #
# ---------------------------------------------- Venue Details --------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


@app.get("/venue", response_model=schemas.Venues)
def get_venues(user: models.User = Depends(get_current_user)):
    try:
        venues = venue.get_all_venues()
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return venues


@app.post("/venue", response_model=None)
def create_venue(venue_info: schemas.Venue):
    try:
        venue_id = venue.create_venue(venue_info)
    except Exception:
        raise HTTPException(status_code=502, detail="SUCKER")

    return {"venue_id": venue_id}


# ---------------------------------------------------------------------------------------------------------------- #
# ----------------------------------------------- Booking -------------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


@app.get("/eventListing/book/{event_id}", response_model=schemas.PreBookingInfo)
def get_pre_booking_information(event_id: int):
    try:
        pre_booking_info = booking.get_pre_booking_info(event_id)
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return pre_booking_info


@app.post("/book/all", response_model=schemas.Bookings)
def get_my_bookings(booking_filter: schemas.BookingFilter, user: models.User = Depends(get_current_user)):
    try:
        my_bookings = booking.get_my_bookings(user, booking_filter)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return my_bookings


@app.get("/book/{bookingId}", response_model=schemas.Booking)
def get_booking_details(booking_id: int, user: models.User = Depends(get_current_user)):
    try:
        booking_details = booking.get_booking_details(booking_id, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return booking_details


@app.post("/book", response_model=schemas.BookingID)
def book_event(booking_request: schemas.MakeBooking, user: models.User = Depends(get_current_user)):
    try:
        return booking.make_booking(booking_request, user)
    except InsuficientFundsException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.delete("/book/{booking_id}", response_model=None)
def cancel_booking(booking_id: int, user: models.User = Depends(get_current_user)):
    try:
        booking.cancel_booking(booking_id, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


# ---------------------------------------------------------------------------------------------------------------- #
# ----------------------------------------------- Referrals ------------------------------------------------------ #
# ---------------------------------------------------------------------------------------------------------------- #


@app.post("/referral", response_model=None)
def create_new_referral(referral_info: schemas.ReferralInfo, user: models.User = Depends(get_current_user)):
    try:
        referral.create_new_referral(referral_info, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except BadGatewayException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.get("/referral/{referral_code}", response_model=None)
def get_referral_discount(referral_code: str, user: models.User = Depends(get_current_user)):
    try:
        return referral.get_referral_discount(referral_code)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.get("/referral", response_model=schemas.HostReferrals)
def get_all_host_referral_codes(user: models.User = Depends(get_current_user)):
    try:
        return referral.get_host_referrals(user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.delete("/referral/{referral_code}", response_model=None)
def deactivate_referral_code(referral_code: str, user: models.User = Depends(get_current_user)):
    try:
        referral.deactivate_referral(referral_code, user)

    except (ForbiddenAccessException, NotFoundException, InvalidInputException, BadGatewayException) as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.put("/referral/{referral_code}", response_model=None)
def reactivate_referral_code(referral_code: str, user: models.User = Depends(get_current_user)):
    try:
        referral.reactivate_referral(referral_code, user)
    except (ForbiddenAccessException, NotFoundException, InvalidInputException, BadGatewayException) as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


# ---------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------------- Search ------------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


@app.post("/", response_model=schemas.EventListingPreviewList)
def get_home_page_events(
    start: Union[schemas.Start, int] = 0, user: Union[models.User, None] = Depends(get_user_or_none)
):
    if type(start) is schemas.Start:
        start = start.start
    if not user or user.user_type == constants.HOST:
        return recommend.get_generic_results(start)
    else:
        return recommend.get_recommended_events(user.user_id, start)


@app.get("/", response_model=str)
def easter_egg(start: Union[schemas.Start, int] = 0, user: Union[models.User, None] = Depends(get_user_or_none)):
    return "Welcome to Eventstar! :)"


@app.get("/trending", response_model=schemas.EventListingPreviewList)
async def get_trending():
    return recommend.get_trending_generic_events()


@app.get("/allEvents", response_model=schemas.EventListingPreviewList)
def get_all_events(user: Union[models.User, None] = Depends(authenticate.get_user_or_none)):
    if not user or user.user_type == constants.HOST:
        return recommend.get_all_generic_events()
    else:
        return recommend.get_all_recommended_events(user.user_id)


@app.get("/trendingEvents/{tag}", response_model=schemas.EventListingPreviewList)
def get_trending_events(tag: str, user: Union[models.User, None] = Depends(authenticate.get_user_or_none)):
    return recommend.get_trending_generic_events(tag)


@app.get("/allTags", response_model=schemas.Tags)
def get_all_tags(user: Union[models.User, None] = Depends(authenticate.get_user_or_none)):
    return recommend.get_all_tags()


@app.post("/search", response_model=schemas.EventListingPreviewList)
def search_events(
    criteria: schemas.sortFilterEventListings, user: Union[models.User, None] = Depends(authenticate.get_user_or_none)
):
    try:
        if not user or user.user_type == constants.HOST:
            return search.run_search_query(criteria)
        else:
            return search.run_search_query(criteria, user.user_id)
    except InvalidInputException as e:
        raise HTTPException(status_code=403, detail=e.message)


@app.post("/allEventsByCoord", response_model=schemas.EventListingPreviewList)
def search_events_by_coord(
    criteria: schemas.eventCoord, user: Union[models.User, None] = Depends(authenticate.get_user_or_none)
):
    try:
        criteria = schemas.sortFilterEventListings(
            searchQuery="", start=0, locationCoord=criteria.locationCoord, sort=""
        )
        if not user or user.user_type == constants.HOST:
            return search.run_search_query(criteria)
        else:
            return search.run_search_query(criteria, user.user_id)
    except InvalidInputException as e:
        raise HTTPException(status_code=403, detail=e.message)


# -------------------------------------------------------------------------------------------------------------------- #
# --------------------------------------------------- Socials -------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------------------------- #


@app.post("/eventListing/review", response_model=None)
def make_review(reviewsDetail: schemas.Reviews, user: models.User = Depends(get_current_user)):
    try:
        reviews_db.make_review(reviewsDetail.eventListingId, reviewsDetail, user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.put("/eventListing/favourite/{event_id}", response_model=None)
def post_favourites(event_id: int, user: models.User = Depends(get_current_user)):
    try:
        socials_db.favourite_event(event_id, user.user_id)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=403, detail=e.message)

    return {}


@app.put("/follow/{hostId}", response_model=None)
async def follow_host(hostId: int, user: models.User = Depends(get_current_user)):
    try:
        follow.follow_unfollow_host(hostId, user)
        await update_follow_count(hostId)
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=e.message)
    return {}


@app.put("/eventListing/react/{event_id}", response_model=None)
def react_to_event(event_id: int, react: schemas.EventReact, user: models.User = Depends(get_current_user)):
    try:
        favourites.react_to_event(event_id, user, react.react)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.post("/review", response_model=None)
def host_reply_to_review(response: schemas.HostRepliesReview, user: models.User = Depends(get_current_user)):
    try:
        reviews_db.reply_to_review(response.reviewId, response, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.get("/eventListing/review/{event_id}", response_model=schemas.AllReviewsWithDetail)
async def get_event_reviews(event_id: int, user: models.User = Depends(get_user_or_none)):
    return reviews_db.get_event_reviews(event_id, user)


@app.put("/review/{reviewId}", response_model=None)
def update_review(reviewId: int, review_detail: schemas.UpdateReview, user: models.User = Depends(get_current_user)):
    try:
        reviews_db.update_reviews(reviewId, review_detail, user)
    except InvalidInputException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    return {}


@app.post("/review/like/{reviewId}", response_model=None)
async def liking_review(reviewId: int, user: models.User = Depends(get_current_user)):
    try:
        reviews_db.like_reviews(reviewId, user.user_id)
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=e.message)

    return {}


@app.post("/review/dislike/{reviewId}", response_model=None)
async def disliking_review(reviewId: int, user: models.User = Depends(get_current_user)):
    try:
        reviews_db.dislike_reviews(reviewId)
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=e.message)

    return {}


# -------------------------------------------------------------------------------------------------------------------- #
# --------------------------------------------------- Analytics ------------------------------------------------------ #
# -------------------------------------------------------------------------------------------------------------------- #


@app.get("/analytics/sales", response_model=schemas.GraphData)
def get_host_daily_sales_graph_data(user: models.User = Depends(get_current_user)):
    try:
        return host_analytics.get_host_daily_sales_graph_data(user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.get("/analytics/followers", response_model=schemas.GraphData)
def get_host_followers_graph_data(user: models.User = Depends(get_current_user)):
    try:
        return follow.get_host_followers_graph_data(user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.get("/analytics/sales/{event_id}", response_model=schemas.EventSalesAnalytics)
def get_event_sales_data(event_id: int, user: models.User = Depends(get_current_user)):

    try:
        return host_analytics.get_event_daily_sales_graph_data(event_id, user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.get("/analytics/sales/ratio/{event_id}", response_model=schemas.EventTotalSalesPerReserve)
def get_event_sales_ratio(event_id: int, user: models.User = Depends(get_current_user)):
    try:
        return host_analytics.get_event_sales_ratio(event_id, user)
    except ForbiddenActionException as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@app.get("/analytics/likeDislike/{event_id}", response_model=schemas.LikesDislikes)
def like_dislike_analytics(event_id: int, user: models.User = Depends(get_current_user)):
    try:
        return event_db.get_event_likes_and_dislikes(event_id, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=403, detail=e.message)


# -------------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------------- Event Chat ------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------------------------- #


@app.get("/eventChat/{eventListingId}", response_model=schemas.ChatMessages)
def get_messages(eventListingId: int, user: models.User = Depends(get_current_user)):
    try:
        return messages.get_messages(eventListingId, user, db.get())
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=e.message)


@app.get("/eventChat", response_model=schemas.EventChat)
def get_chat_info(user: models.User = Depends(get_current_user)):
    return messages.get_chats(user, db.get())


@app.websocket("/ws/{event_id}")
async def websocket_endpoint(websocket: WebSocket, event_id: int):
    db_session = SessionLocal()
    await manager.connect(websocket, event_id)
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            if "type" in data.keys() and data["type"] == "connect":
                pass
            else:
                error = messages.update_chat(schemas.CreateChatMessage.parse_obj(data), db_session)
                await manager.broadcast(json.dumps(error), event_id)
            db_session.commit()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        db_session.close()


async def update_follow_count(host_id: int):
    curr_follower_count = messages.live_follower_count(host_id, db.get())
    await count_manager.broadcast(json.dumps(curr_follower_count), host_id)


@app.websocket("/ws/followCount/{host_id}")
async def websocket_count_endpoint(websocket: WebSocket, host_id: int):
    await count_manager.connect(websocket, host_id)
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            if "type" in data.keys() and data["type"] == "connect":
                pass
    except WebSocketDisconnect:
        count_manager.disconnect(websocket)


# -------------------------------------------------------------------------------------------------------------------- #
# ------------------------------------------------- Surveys ------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------------------------- #


@app.post("/survey", response_model=None)
async def new_survey(
    survey_details: schemas.SurveyObject,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_current_user),
):
    try:
        create_surveys.new_survey(survey_details, user, background_tasks)
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=403, detail=e.message)


@app.delete("/survey/{event_id}", response_model=None)
async def delete_survey(event_id: int, user: models.User = Depends(get_current_user)):
    try:
        delete_surveys.remove_survey(event_id, user)
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/survey/{event_id}", response_model=schemas.ListGetSurvey)
async def get_survey(event_id: int, user: models.User = Depends(get_current_user)):
    try:
        survey_obj = get_surveys.get_survey(event_id, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputException as e:
        raise HTTPException(status_code=400, detail=str(e))

    return survey_obj


@app.post("/survey/submit", response_model=None)
async def submit_survey(customer_answer: schemas.SurveySubmit, user: models.User = Depends(get_current_user)):
    try:
        submit_surveys.send_survey(customer_answer, user)
    except ForbiddenAccessException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidRequestException as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------------------------------------------- #
# ----------------------------------------------- FastAPI -------------------------------------------------------- #
# ---------------------------------------------------------------------------------------------------------------- #


# TODO: get this working in future
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="COMP3900 Eventstar Server - The Binary Brotherhood.")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Specify the port address")
    parser.add_argument("--host", default="localhost", help="Specify the host address")
    parser.add_argument("--reload", "-r", action="store_true", help="Enable Server Reload Mode")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
