from breathecode.notify.actions import send_email_message
from django.contrib import messages
import logging
from breathecode.authenticate.actions import create_token
from .models import Answer
from breathecode.admissions.models import CohortUser

logger = logging.getLogger(__name__)

strings = {
    "es": {
        "first": "¿Qué tan probable es que recomiendes",
        "second": " a tus amigos y familiares?",
    },
    "en": {
        "first": "How likely are you to recommend",
        "second": "to your friends and family?",
    }
}

def send_survey(user, cohort=None):

    answer = Answer(user = user)
    if cohort is not None: 
        answer.cohort = cohort
    else:
        cohorts = CohortUser.objects.filter(user__id=user.id).order_by("-cohort__kickoff_date")
        _count = cohorts.count()
        if _count == 1:
            _cohort = cohorts.first().cohort
            answer.cohort = _cohort

    if answer.cohort is None:
        messages.error('Impossible to determine the student cohort, maybe it has more than one, or cero.')
        logger.warning(f'Impossible to determine the student cohort, maybe it has more than one, or cero.')
        answer.save()
        return False

    answer.academy = answer.cohort.academy
    question = strings[answer.cohort.language]["first"] + " " + answer.cohort.academy.name + " " + strings[answer.cohort.language]["second"]
    answer.title = question
    answer.save()

    token = create_token(user, hours_length=48)
    data = {
        "QUESTION": question,
        "SUBJECT": question,
        "LINK": f"https://nps.breatheco.de/{answer.id}?token={token.key}"
    }

    send_email_message("nps", user.email, data)

    answer.status = "SENT"
    answer.save()

    return True
    # keep track of sent survays until they get answered


def answer_survey(user, data):
    answer = Answer.objects.create(**{ **data, "user": user })

    # log = SurveyLog.objects.filter(
    #     user__id=user.id, 
    #     cohort__id=answer.cohort.id, 
    #     academy__id=answer.academy.id,
    #     mentor__id=answer.academy.id
    # )