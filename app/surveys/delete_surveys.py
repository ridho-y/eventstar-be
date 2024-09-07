from .. import models
from .. import exceptions
from . import surveys_db
from ..auth import auth_db


def remove_survey(event_id: int, user: models.User):
    if not auth_db.check_user_is_host(user, event_id):
        raise exceptions.ForbiddenAccessException("You must be the host of the event to make a survey")

    surveys_db.delete_survey(event_id)
