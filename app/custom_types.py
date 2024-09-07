from app import schema_validations


class Email(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_email


class Name(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_name


class OptEmail(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_optional_email


class OptLink(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_optLink


class MemberType(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_memberType


class Rating(float):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_rating


class Phone(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_phone


class State(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_state


class Country(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_country


class Postcode(int):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_postcode


class ExpiryMonth(int):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_expiry_month


class ExpiryYear(int):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_expiry_year


class CardNumber(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_card_number


class OnlineLink(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_link


class YoutubeLink(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_youtube_link


class EventType(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_event_type


class SearchString(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_search


class ShortString(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_short_string


class LongString(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_long_string


class React(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_react


class RequiredShortStr(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_required_string


class PostiveInt(int):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_postive_int


class MessageType(str):
    @classmethod
    def __get_validators__(cls):
        yield schema_validations.validate_message_type
