from fastapi import BackgroundTasks

from .. import exceptions, models, schemas
from ..auth import auth_db
from . import surveys_db


def new_survey(survey_details: schemas.SurveyObject, user: models.User, background_tasks: BackgroundTasks):
    if not auth_db.check_user_is_host(user, survey_details.eventListingId):
        raise exceptions.ForbiddenAccessException("You must be the host of the event to make a survey")

    if surveys_db.get_existing_survey(survey_details.eventListingId, user):
        raise exceptions.InvalidInputException("A survey already exists for this event by this host")

    # Ensure the survey has the proper number of questions
    if not (1 <= len(survey_details.survey) <= 5):
        raise exceptions.InvalidRequestException("You must specify between 1 and 5 questions")

    # Create new Survey
    new_survey = surveys_db.create_and_save_survey(survey_details.eventListingId, user)

    # Add questions to survey
    surveys_db.add_questions_to_survey(survey_details, new_survey.survey_id)

    surveys_db.set_made_survey_to_true(survey_details.eventListingId)

    # delete all event response(ensure that when new survey is created customer can still respond)
    surveys_db.delete_customer_response_trigger(survey_details.eventListingId)

    # Add background task
    background_tasks.add_task(surveys_db.send_survey_email, new_survey.survey_id)

    # Retrieve all the survey questions added to the new_survey
    survey_questions = surveys_db.get_survey_questions(new_survey.survey_id)

    survey_list = []
    for survey_question in survey_questions:
        survey = schemas.Survey(question=survey_question.question, shortInput=survey_question.short_input)
        survey_list.append(survey)

    # Create a new schemas.SurveyObject instance using the survey details and the new survey id
    return schemas.SurveyObject(eventListingId=survey_details.eventListingId, survey=survey_list)
