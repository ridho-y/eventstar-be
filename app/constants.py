from enum import Enum
import os

# ------------------- Authentication -----------------------
ACCESS_TOKEN_EXPIRE_MINUTES = 180


# ------------------- Validation ---------------------------
MAX_USERNAME_LEN = 64
MIN_USERNAME_LEN = 5
MAX_PASSWORD_LEN = 255
MAX_MESSAGE_LEN = 500
MIN_PASSWORD_LEN = 8
INVALID_USERNAME_PASSWORD_SUBSTR_LEN = 6


# ------------------- Company Email  -------------------------
EVENTSTAR_EMAIL_ADDRESS = os.environ.get("EVENTSTAR_EMAIL")
EVENTSTAR_EMAIL_PASSWORD = os.environ.get("EVENTSTAR_EMAIL_PASSWORD")
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587


# ------------------- Reset Password Code -------------------------
DEFAULT_CODE_LENGTH = 6


# ------------------- Search -------------------------
class SortOption(Enum):
    UPCOMING = "upcoming"
    MOST_LIKED = "mostLiked"
    LOWEST_PRICE = "lowestPrice"
    HIGHEST_PRICE = "highestPrice"
    ALPHABETICAL = "alphabetical"
    ALPHABETICAL_REVERSE = "alphabeticalReverse"
    RELEVANCE = "relevance"


TRENDING = 8
SEARCH_RESULTS = 16
START = 0
TITLE_TO_COMPARE = "event_title_to_compare"
DESCRIPTION_TO_COMPARE = "event_description_to_compare"
SIMILARITY_THRESHOLD = 0.8
HIGH_SCORE = 1.5
LIKE_WEIGHT = 2
POPULARITY_WEIGHT = 0.5
FOLLOW_WEIGHT = 1

# ------------------------ Event Types ----------------------------
ONLINE = "online"
INPERSON = "inpersonNonSeated"
SEATED = "inpersonSeated"

# ------------------------ User Types ----------------------------
HOST = "host"
CUSTOMER = "user"

# ------------------------ Media Types ----------------------------
IMAGE = "image"
YOUTUBE = "youtube"

# ------------------------ Default Images ----------------------------
DEFAULT_BANNER = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRqq1GYuWks14ppG0FRAZsG1DPDNFJDU4inFA&s"
DEFAULT_THUMBNAIL = "https://static.vecteezy.com/system/resources/thumbnails/022/014/063/small_2x/missing-picture-page-for-website-design-or-mobile-app-design-no-image-available-icon-vector.jpg"


# ------------------------ Financials ----------------------------
MAX_BALANCE = 10 ** 8
TRANSACTION_RESULTS = 10
SALES_DATA_LIMIT = 15


# ------------------------ Booking ----------------------------
BOOKING_CUTOFF_DAYS = 7


# ------------------------ Socials ----------------------------
LIKE = "like"
DISLIKE = "dislike"
NONE = "none"


# ------------------------ Deleted Users ----------------------------
DELETED_USER = "DELETED USER"
DELETED_USER_EMAIL = "deleteduser@deleteduser.event"


# ------------------- Event Chat -------------------------
class EventChatRequest(Enum):
    NEW = "newMessage"
    EDIT = "editMessage"
    DELETE = "deleteMessage"
    LIKE = "toggleLike"
    PIN = "togglePin"


class BroadcastType(Enum):
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
