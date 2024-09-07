from .. import models
from .. import exceptions
from . import surveys_db
from ..auth import auth_db
from ..booking import booking_db
from ..profile import profile_db
from ..events import event_db


def get_survey(eventListingId: int, user: models.User):

    # CHECK IF HOST OR IF CUSTOMER
    if not (
        booking_db.user_has_booked(user.user_id, eventListingId) or auth_db.check_user_is_host(user, eventListingId)
    ):
        raise exceptions.ForbiddenAccessException("Must be the Host or a paying customer")

    # Get the survey associated with the event
    survey = surveys_db.get_event_survey(eventListingId)
    if not survey:
        raise exceptions.InvalidInputException(f"No survey found for event id {eventListingId}")

    # Get the questions for the survey
    survey_questions = surveys_db.get_survey_questions(survey.survey_id)

    survey_response = {
        "orgName": profile_db.get_host_org_name(eventListingId),
        "title": event_db.get_event(eventListingId).title,
        "survey": [
            {
                "questionId": question.survey_question_id,
                "question": question.question,
                "shortInput": question.short_input,
            }
            for question in survey_questions
        ],
    }

    return survey_response
