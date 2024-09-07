from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Dict, Optional, Union, List
from app import constants, custom_types


# ------------------------------------------------------------------------------------------------- #
# --------------------------------------- Authenication ------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class JWTToken(BaseModel):
    memberId: int
    memberType: custom_types.MemberType
    expiry: datetime = None


class SignUpRequest(BaseModel):
    firstName: custom_types.Name
    lastName: custom_types.Name
    email: custom_types.Email
    password: custom_types.ShortString
    username: custom_types.ShortString
    memberType: custom_types.MemberType


class TwoFa(BaseModel):
    code: str


class Confirmation(BaseModel):
    value: bool


class ResetEmail(BaseModel):
    email: custom_types.Email


# ------------------------------------------------------------------------------------------------- #
# --------------------------------------- Profile ------------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class ProfileInfo(BaseModel):
    memberId: int
    isHost: bool
    firstName: custom_types.Name
    lastName: custom_types.Name
    username: custom_types.ShortString
    email: custom_types.Email
    balance: float
    orgName: Optional[custom_types.ShortString]
    description: Optional[custom_types.LongString]
    orgEmail: Optional[custom_types.OptEmail]
    banner: Optional[custom_types.OptLink]
    noFollowers: Optional[int]
    rating: Optional[custom_types.Rating]
    noEvents: Optional[int]


class UpdateProfileDetails(BaseModel):
    firstName: Optional[custom_types.ShortString]
    lastName: Optional[custom_types.ShortString]
    username: Optional[custom_types.ShortString]
    email: Optional[custom_types.OptEmail]
    orgName: Optional[custom_types.ShortString]
    description: Optional[custom_types.LongString]
    orgEmail: Optional[custom_types.OptEmail]
    banner: Optional[custom_types.OptLink]


class ShortProfileInfo(BaseModel):
    firstName: custom_types.Name
    isHost: bool
    memberId: int


class UpdatePass(BaseModel):
    old_password: custom_types.ShortString
    new_password: custom_types.ShortString


class ResetPasswordAndCode(BaseModel):
    email: Optional[custom_types.Email]
    code: custom_types.ShortString
    new_password: custom_types.ShortString


class FollowingHostProfile(BaseModel):
    hostId: int
    orgName: Optional[custom_types.Name]


class FollowingHostProfileList(BaseModel):
    following: List[FollowingHostProfile]


# ------------------------------------------------------------------------------------------------- #
# ------------------------------------------ Billing ---------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class BillingAddress(BaseModel):
    firstName: custom_types.Name
    lastName: custom_types.Name
    country: custom_types.Country
    streetLine1: custom_types.ShortString
    streetLine2: Optional[custom_types.ShortString]
    suburb: custom_types.ShortString
    state: custom_types.State
    postcode: custom_types.Postcode
    email: custom_types.Email
    phone: custom_types.Phone


class BillingInfo(BaseModel):
    billingId: Optional[int]
    cardNumber: custom_types.CardNumber
    expiryMonth: custom_types.ExpiryMonth
    expiryYear: custom_types.ExpiryYear
    billingAddress: BillingAddress


class UpdateBillingAddress(BaseModel):
    firstName: Optional[custom_types.Name]
    lastName: Optional[custom_types.Name]
    country: Optional[custom_types.Country]
    streetLine1: Optional[custom_types.ShortString]
    streetLine2: Optional[Union[custom_types.ShortString, None]]
    suburb: Optional[custom_types.ShortString]
    state: Optional[custom_types.State]
    postcode: Optional[custom_types.Postcode]
    email: Optional[custom_types.Email]
    phone: Optional[custom_types.Phone]


class UpdateBillingInfo(BaseModel):
    cardNumber: Optional[custom_types.CardNumber]
    expiryMonth: Optional[custom_types.ExpiryMonth]
    expiryYear: Optional[custom_types.ExpiryYear]
    billingAddress: Optional[UpdateBillingAddress]


class AllBillingInfo(BaseModel):
    billingInfo: List[BillingInfo]
    balance: float


class UpdateBalance(BaseModel):
    billingId: Optional[int] = None
    amount: float


# ------------------------------------------------------------------------------------------------- #
# ------------------------------------------ Event FAQs ------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class FaqId(BaseModel):
    faqId: int


class Faq(BaseModel):
    faqId: Optional[int]
    question: Optional[custom_types.ShortString]
    answer: Optional[custom_types.ShortString]


class FAQModel(BaseModel):
    question: custom_types.ShortString
    answer: custom_types.ShortString


# ------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Event Types ------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class Reserve(BaseModel):
    name: custom_types.ShortString
    description: Optional[custom_types.LongString] = None
    cost: float
    quantity: Optional[int] = 0
    sections: Optional[List[custom_types.ShortString]] = []


class EventReserve(BaseModel):
    name: custom_types.ShortString
    description: Optional[custom_types.LongString] = None
    cost: float
    tickets: Optional[int] = 0
    sections: Optional[List[custom_types.ShortString]] = []


class CreateOnlineEventSpecifics(BaseModel):
    onlineLink: custom_types.OnlineLink
    cost: Optional[float] = 0.0
    quantity: Optional[int] = 0


class OnlineEventSpecifics(BaseModel):
    onlineLink: custom_types.OnlineLink
    cost: Optional[float] = 0.0
    tickets: Optional[int] = 0


class CreateInPersonEventSpecifics(BaseModel):
    location: custom_types.ShortString
    locationCoord: str
    reserves: Optional[List[Reserve]]


class InPersonEventSpecifics(BaseModel):
    location: custom_types.ShortString
    locationCoord: str
    reserves: Optional[List[EventReserve]]


class CreateSeatedEventSpecifics(BaseModel):
    venueId: int
    venue: Optional[custom_types.ShortString]
    reserves: List[Reserve]


class SeatedEventSpecifics(BaseModel):
    venueId: int
    venue: Optional[custom_types.ShortString]
    reserves: List[EventReserve]


# ------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Venues ------------------------------------------------ #
# ------------------------------------------------------------------------------------------------- #


class VenueSection(BaseModel):
    sectionName: custom_types.ShortString
    totalSeats: int


class Venue(BaseModel):
    name: custom_types.ShortString
    venueId: Optional[int]
    location: Optional[custom_types.ShortString]
    locationCoords: Optional[custom_types.ShortString]
    sections: List[VenueSection]


class Venues(BaseModel):
    venues: List[Venue]


# ------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Events ------------------------------------------------ #
# ------------------------------------------------------------------------------------------------- #


class Tags(BaseModel):
    tags: List[str]


class EventId(BaseModel):
    eventListingId: int


class EventListings(BaseModel):
    eventListings: List[int]


class CreateEventListing(BaseModel):
    title: custom_types.RequiredShortStr
    startDateTime: datetime
    endDateTime: datetime
    type: custom_types.EventType
    summary: custom_types.ShortString
    description: custom_types.LongString
    images: List[custom_types.OnlineLink]
    tags: List[custom_types.Name]
    youtubeLinks: List[custom_types.YoutubeLink]
    faq: Optional[List[FAQModel]] = Field(default_factory=list)
    online: Optional[CreateOnlineEventSpecifics] = None
    inpersonNonSeated: Optional[CreateInPersonEventSpecifics] = None
    inpersonSeated: Optional[CreateSeatedEventSpecifics] = None


class EventListing(BaseModel):
    eventListingId: Optional[int]
    memberId: Optional[int]
    title: custom_types.RequiredShortStr
    startDateTime: datetime
    endDateTime: datetime
    type: custom_types.EventType
    summary: custom_types.ShortString
    description: custom_types.LongString
    images: List[custom_types.OnlineLink] = [constants.DEFAULT_THUMBNAIL]
    tags: List[custom_types.Name]
    youtubeLinks: List[custom_types.YoutubeLink]
    faq: Optional[List[FAQModel]] = Field(default_factory=list)
    online: Optional[OnlineEventSpecifics] = None
    inpersonNonSeated: Optional[InPersonEventSpecifics] = None
    inpersonSeated: Optional[SeatedEventSpecifics] = None
    ticketsAvailable: int = 0
    minimumCost: float = 0


class HostInformation(BaseModel):
    orgName: custom_types.ShortString
    description: custom_types.LongString
    orgEmail: custom_types.OptEmail
    banner: custom_types.OptLink
    noFollowers: int
    rating: float
    noEvents: int


class UserInfoEventListing(BaseModel):
    reaction: custom_types.React
    favourited: bool
    followsHost: bool
    boughtTicket: bool
    hasReviewed: bool


class Announcements(BaseModel):
    eventListingId: Optional[int]
    title: custom_types.RequiredShortStr
    date: Optional[datetime]
    message: custom_types.LongString


class EventDetails(BaseModel):
    title: custom_types.RequiredShortStr
    startDateTime: datetime
    endDateTime: datetime
    type: custom_types.EventType
    editable: bool
    averageRating: Optional[float]
    cancelled: bool
    eventListingId: Optional[int]
    memberId: int
    summary: Optional[custom_types.ShortString]
    description: custom_types.LongString
    tags: List[custom_types.Name]
    images: List[custom_types.OnlineLink]
    youtubeLinks: Optional[List[custom_types.YoutubeLink]]
    faq: Optional[List[FAQModel]]
    noLikes: int
    noDislikes: int
    minimumCost: float
    edited: bool
    ticketsLeft: int
    rating: float
    hostInfo: HostInformation
    userInfo: Optional[UserInfoEventListing]
    announcements: Optional[List[Announcements]]
    online: Optional[OnlineEventSpecifics]
    inpersonNonSeated: Optional[InPersonEventSpecifics]
    inpersonSeated: Optional[SeatedEventSpecifics]
    surveyMade: bool = False


class EventListingPreview(BaseModel):
    eventListingId: int
    thumbnail: str = constants.DEFAULT_THUMBNAIL
    orgName: Optional[custom_types.ShortString]
    noLikes: int
    noFollowers: int
    minimumCost: Optional[float]
    location: Optional[custom_types.ShortString]
    hostId: int
    title: Optional[custom_types.ShortString]
    startDateTime: str
    endDateTime: str
    type: custom_types.EventType


class EventListingPreviewList(BaseModel):
    eventListings: List[EventListingPreview]


class EventUpdate(BaseModel):
    title: Optional[custom_types.ShortString]
    startDateTime: Optional[datetime] = None
    endDateTime: Optional[datetime] = None
    summary: Optional[custom_types.ShortString] = None
    description: Optional[custom_types.LongString] = None
    images: Optional[List[custom_types.OnlineLink]] = None
    tags: Optional[List[custom_types.Name]] = None
    youtubeLinks: Optional[List[custom_types.YoutubeLink]] = None
    faq: Optional[List[FAQModel]] = None


# ------------------------------------------------------------------------------------------------- #
# --------------------------------------- Event Search -------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class FilterListings(BaseModel):
    dateStart: Optional[Union[datetime, str]]
    dateEnd: Optional[Union[datetime, str]]
    priceStart: Optional[float]
    priceEnd: Optional[float]
    type: Optional[custom_types.EventType]
    tags: Optional[List[custom_types.Name]]
    kmNearMe: Optional[float]
    ratingAtLeast: Optional[custom_types.Rating]


class sortFilterEventListings(BaseModel):
    searchQuery: Optional[custom_types.SearchString]
    start: custom_types.PostiveInt
    locationCoord: Optional[custom_types.ShortString]
    filter: Optional[FilterListings]
    sort: Optional[custom_types.ShortString]


class SortEventListings(BaseModel):
    sort: Optional[custom_types.ShortString]


class eventCoord(BaseModel):
    locationCoord: custom_types.ShortString


class EventReact(BaseModel):
    react: custom_types.React


# ------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Event Reviews ------------------------------------------ #
# ------------------------------------------------------------------------------------------------- #


class HostReply(BaseModel):
    orgName: custom_types.Name
    date: datetime
    edited: bool
    reply: custom_types.ShortString


class UserInfo(BaseModel):
    userLiked: bool = False


class ReviewDetails(BaseModel):
    eventInfo: EventListingPreview
    rating: custom_types.Rating
    review: custom_types.LongString
    reviewId: custom_types.PostiveInt
    eventListingId: custom_types.PostiveInt
    hostId: custom_types.PostiveInt
    orgName: custom_types.Name
    firstName: custom_types.Name
    lastName: custom_types.Name
    memberId: custom_types.PostiveInt
    date: datetime
    edited: bool
    likes: custom_types.PostiveInt
    host: Optional[HostReply] = None
    userInfo: Optional[UserInfo] = None


class AllReviewsWithDetail(BaseModel):
    reviews: List[ReviewDetails]


class Reviews(BaseModel):
    eventListingId: int
    rating: custom_types.Rating
    review: custom_types.ShortString


class UpdateReview(BaseModel):
    rating: Optional[custom_types.Rating]
    review: custom_types.ShortString


class HostRepliesReview(BaseModel):
    reviewId: custom_types.PostiveInt
    response: custom_types.ShortString


# ------------------------------------------------------------------------------------------------- #
# --------------------------------------- Host Profile -------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class FollowsHost(BaseModel):
    followsHost: bool


class HostPublicProfileInformation(BaseModel):
    reviews: List[ReviewDetails]
    userInfo: Optional[FollowsHost]
    orgName: Optional[custom_types.ShortString] = None
    description: Optional[custom_types.LongString]
    orgEmail: Optional[custom_types.OptEmail]
    banner: Optional[custom_types.OptLink]
    noFollowers: custom_types.PostiveInt
    rating: Optional[custom_types.Rating]
    noEvents: custom_types.PostiveInt


# ------------------------------------------------------------------------------------------------- #
# --------------------------------------- Pre Booking Info ---------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class ReservePreBookingInfo(BaseModel):
    reserveName: custom_types.Name
    ticketsLeft: custom_types.PostiveInt
    cost: float
    description: custom_types.LongString


class SectionPreBookingInfo(BaseModel):
    sectionName: custom_types.Name
    ticketsLeft: custom_types.PostiveInt
    cost: float
    reserve: custom_types.ShortString
    description: custom_types.LongString


class NonSeatedBookingInfo(BaseModel):
    reserves: List[ReservePreBookingInfo]


class SeatedBookingInfo(BaseModel):
    sections: List[SectionPreBookingInfo]


class PreBookingInfo(BaseModel):
    nonSeated: Optional[NonSeatedBookingInfo]
    seated: Optional[SeatedBookingInfo]
    eventInfo: EventListingPreview


# ------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Booking ----------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class BookingReserveInfo(BaseModel):
    reserve: custom_types.Name
    tickets: custom_types.PostiveInt
    cost: float
    description: custom_types.LongString
    seats: Optional[List[custom_types.ShortString]]


class Booking(BaseModel):
    bookingId: custom_types.PostiveInt
    cancelled: bool
    bookingDate: datetime
    eventId: custom_types.PostiveInt
    totalCost: float
    totalQuantity: custom_types.PostiveInt
    referralCode: Optional[str]
    amountSaved: Optional[float]
    percentageOff: Optional[float] = 0
    reserves: List[BookingReserveInfo]
    eventInfo: EventListingPreview


class Bookings(BaseModel):
    bookings: List[Booking]


class BookingReserves(BaseModel):
    reserveName: custom_types.ShortString
    quantity: custom_types.PostiveInt
    section: Optional[custom_types.ShortString]

    reserve_id: Optional[int] = 0
    cost: Optional[float] = 0
    event_section_id: Optional[int] = 0
    venue_section_id: Optional[int] = 0


class MakeBookingReserves(BaseModel):
    reserveName: custom_types.ShortString
    quantity: custom_types.PostiveInt
    section: Optional[custom_types.ShortString]


class MakeBooking(BaseModel):
    reserves: List[MakeBookingReserves]
    referralCode: Optional[custom_types.ShortString] = ""
    eventListingId: custom_types.PostiveInt


class MakeBaseBooking(BaseModel):
    eventId: int
    userId: int
    date: datetime
    totalCost: float
    totalQuantity: int
    referralCode: str
    amountSaved: float


class BookingID(BaseModel):
    bookingId: custom_types.PostiveInt


class BookingFilter(BaseModel):
    dateStart: Optional[date]
    searchstr: Optional[custom_types.SearchString]


# ------------------------------------------------------------------------------------------------- #
# -------------------------------------- Transactions --------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class Transaction(BaseModel):
    dateTime: datetime
    description: custom_types.LongString
    credit: float = 0
    debit: float = 0
    balance: float = 0


class Transactions(BaseModel):
    transactions: List[Transaction]


# ------------------------------------------------------------------------------------------------- #
# ---------------------------------------- Referrals ---------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class ReferralInfo(BaseModel):
    referralCode: custom_types.ShortString
    percentageOff: float
    referrerCut: float
    name: custom_types.Name
    payIdPhone: custom_types.Phone
    amountPaid: Optional[float]
    noUsed: Optional[float]
    isActive: Optional[bool]


class HostReferrals(BaseModel):
    activeReferrals: List[ReferralInfo]
    inactiveReferrals: List[ReferralInfo]


class Discount(BaseModel):
    discount: float


class Start(BaseModel):
    start: custom_types.PostiveInt


# ------------------------------------------------------------------------------------------------- #
# --------------------------------------- Event Chat ---------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class Liked(BaseModel):
    liked: bool


class ChatEventInfo(BaseModel):
    eventListingId: int
    hostId: Optional[int]
    thumbnail: str = constants.DEFAULT_THUMBNAIL
    title: str


class CreateChatMessage(BaseModel):
    token: str
    requestType: custom_types.MessageType
    eventListingId: int
    message: Optional[custom_types.LongString]
    replyMessageId: Optional[int]
    files: Optional[List[custom_types.OnlineLink]]
    messageId: Optional[int]


class Message(BaseModel):
    memberId: int
    messageId: int
    dateTime: datetime
    username: str
    message: custom_types.LongString
    replyMessageId: Optional[int]
    files: List[custom_types.OnlineLink]
    noLikes: int
    edited: bool
    pinned: bool
    deleted: bool


class ChatMessage(BaseModel):
    type: str
    messageId: int
    message: Message


class MessageInfo(BaseModel):
    memberId: int
    messageId: int
    dateTime: datetime
    username: str
    message: custom_types.LongString
    replyMessageId: Optional[int]
    files: List[custom_types.OnlineLink]
    noLikes: int
    edited: bool
    pinned: bool
    userInfo: Liked
    deleted: bool


class ChatMessages(BaseModel):
    messages: Dict[int, MessageInfo]
    eventInfo: ChatEventInfo


class EventChat(BaseModel):
    eventChatPreviews: List[ChatEventInfo]


class FollowerCount(BaseModel):
    hostId: int
    followerCount: int


# --------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Analytics ----------------------------------------------- #
# --------------------------------------------------------------------------------------------------- #


class DataPoint(BaseModel):
    xValue: date
    yValue: Union[int, float]


class GraphData(BaseModel):
    data: List[DataPoint]


class EventReserveSalesAnalytics(BaseModel):
    id: custom_types.ShortString
    data: List[DataPoint]


class EventSalesAnalytics(BaseModel):
    data: List[EventReserveSalesAnalytics]


class EventReserveSalesTotal(BaseModel):
    id: custom_types.ShortString
    tickets: custom_types.PostiveInt


class EventTotalSalesPerReserve(BaseModel):
    data: List[EventReserveSalesTotal]


class LikesDislikes(BaseModel):
    likes: int
    dislikes: int


# ------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Survey  ----------------------------------------------- #
# ------------------------------------------------------------------------------------------------- #


class Survey(BaseModel):
    question: custom_types.ShortString
    shortInput: bool


class SurveyObject(BaseModel):
    eventListingId: int
    survey: List[Survey]


class GetSurvey(BaseModel):
    questionId: int
    shortInput: bool
    question: custom_types.ShortString


class SurveyResponse(BaseModel):
    questionId: str
    answer: custom_types.LongString


class SurveySubmit(BaseModel):
    eventListingId: int
    survey: List[SurveyResponse]


class ListGetSurvey(BaseModel):
    survey: List[GetSurvey]
    orgName: str
    title: str
