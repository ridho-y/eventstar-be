from ..booking import booking_db
from .. import models, schemas
from .. import exceptions
from .. import helpers
from . import surveys_db
from datetime import datetime
from ..events import event_db


def send_survey(customer_answer: schemas.SurveySubmit, user: models.User):

    # HAS TO BE A PAYING CUSTOMER
    if not booking_db.user_has_booked(user.user_id, customer_answer.eventListingId):
        raise exceptions.ForbiddenAccessException("Must be the Host or a paying customer")

    event = event_db.get_event(customer_answer.eventListingId)

    # CAN ONLY SUBMIT AFTER EVENT HAS ENDED
    if datetime.now() < event.end_time:
        raise exceptions.ForbiddenAccessException("Event has not yet ended")

    # IF SURVEY DONT EXIST THEN ERROR:
    survey = surveys_db.get_event_survey(customer_answer.eventListingId)
    if not survey:
        raise exceptions.InvalidRequestException("No survey for this event")

    # BACKEND EMAILS THE HOST if user not yet submit
    if surveys_db.check_user_already_submit(customer_answer.eventListingId, user.user_id):
        raise exceptions.InvalidRequestException("User has already submitted a response")

    host_email = event.host.user.email
    body = "Customer Survey Responses:\n"

    for i, response in enumerate(customer_answer.survey, 1):
        question_text = surveys_db.get_question_text_by_id(response.questionId)
        if question_text is not None:
            body += f"Q{i} (Question Id: {response.questionId}, Question: {question_text}): {response.answer}\n"
        else:
            body += f"Q{i} (Question Id: {response.questionId}): {response.answer}\n"

    surveys_db.add_survey_response(user.user_id, survey.survey_id)

    helpers.send_email_with_gmail(to=host_email, subject="Customer Survey Response", body=body)
