from typing import Dict
import asyncio
import datetime
from sqlalchemy import delete, and_

from .. import exceptions, models, schemas
from ..database import db
from ..events import event_db
from .. import helpers


active_survey_tasks: Dict[int, asyncio.Task] = {}


def add_questions_to_survey(survey_details: schemas.SurveyObject, survey_id: int):
    for survey in survey_details.survey:
        new_question = models.SurveyQuestion(
            question=survey.question, survey_id=survey_id, short_input=survey.shortInput
        )
        db.get().add(new_question)

    db.get().commit()


def get_event_survey(event_id: int):
    return db.get().query(models.Survey).filter(models.Survey.event_id == event_id).first()


def delete_customer_response_trigger(event_id: int):
    survey = db.get().query(models.Survey.survey_id).filter(models.Survey.event_id == event_id).first()

    if survey:
        db.get().execute(delete(models.SurveyResponses).where(models.SurveyResponses.survey_id == survey.survey_id))
        db.get().commit()


def get_existing_survey(event_id: int, host: models.Host):
    existing_survey = (
        db.get()
        .query(models.Survey)
        .filter(and_(models.Survey.event_id == event_id, models.Survey.host_id == host.host_id))
        .first()
    )
    return existing_survey


def create_and_save_survey(event_id: int, host: models.Host):
    new_survey = models.Survey(event_id=event_id, host_id=host.host_id)
    db.get().add(new_survey)
    db.get().commit()
    db.get().refresh(new_survey)
    return new_survey


async def send_survey_email(survey_id: int, delay: int = 5):
    active_survey_tasks[survey_id] = asyncio.create_task(_send_survey_email(survey_id, delay))


async def _send_survey_email(survey_id: int, delay: int = 5):
    while True:
        await asyncio.sleep(delay)

        survey = db.get().query(models.Survey).filter_by(survey_id=survey_id).first()

        if survey is None:
            continue

        event_end_time_result = event_db.get_event_end_time(survey.event_id)
        if event_end_time_result is None:
            print(f"No event end time found for event {survey.event_id}, exiting process")
            break

        now = datetime.datetime.now().astimezone()
        event_end_time = event_end_time_result.replace(tzinfo=now.tzinfo)

        if now >= event_end_time:

            customers_email = event_db.get_event_customer_emails(survey.event_id)

            helpers.send_email_with_gmail(
                to=customers_email,
                subject="New Survey Available",
                body=f"Hello, A new survey is available. Please visit the following link to answer it: http://localhost:3000/survey/{survey.event_id}",
            )
            break

    del active_survey_tasks[survey_id]


def get_survey_questions(survey_id: int):
    return db.get().query(models.SurveyQuestion).filter_by(survey_id=survey_id).all()


def delete_survey(event_id: int):
    survey = db.get().query(models.Survey).filter(models.Survey.event_id == event_id).first()

    if survey is None:
        raise exceptions.InvalidInputException(f"No survey found for event id {event_id}")

    survey_task = active_survey_tasks.get(survey.survey_id)
    if survey_task is not None:
        survey_task.cancel()

    survey_questions = (
        db.get().query(models.SurveyQuestion).filter(models.SurveyQuestion.survey_id == survey.survey_id).all()
    )

    for question in survey_questions:
        db.get().delete(question)

    set_made_survey_to_false(event_id)

    db.get().flush()
    db.get().delete(survey)
    db.get().commit()


def check_user_already_submit(event_id: int, user_id: int):
    return (
        db.get()
        .query(models.SurveyResponses)
        .join(models.Survey)
        .filter(and_(models.SurveyResponses.customer_id == user_id, models.Survey.event_id == event_id))
        .first()
    )


def get_question_text_by_id(question_id: int):
    survey_question = (
        db.get()
        .query(models.SurveyQuestion.question)
        .filter(models.SurveyQuestion.survey_question_id == question_id)
        .first()
    )
    if survey_question:
        return survey_question.question
    return None


def add_survey_response(customer_id: int, survey_id: int):
    survey_response = models.SurveyResponses(customer_id=customer_id, survey_id=survey_id)
    db.get().add(survey_response)
    db.get().commit()


def get_made_survey_bool(event_id: int):
    result = db.get().query(models.Event.survey_made).filter(models.Event.event_id == event_id).first()
    return result[0] if result else None


def set_made_survey_to_true(event_id: int):
    event = db.get().query(models.Event).filter(models.Event.event_id == event_id).first()
    if event:
        event.survey_made = True
        db.get().commit()


def set_made_survey_to_false(event_id: int):
    event = db.get().query(models.Event).filter(models.Event.event_id == event_id).first()
    if event:
        event.survey_made = False
        db.get().commit()
