import logging, os
from celery import shared_task, Task
from django.contrib.auth.models import User
from .actions import set_gitpod_user_expiration, add_to_organization, remove_from_organization
from breathecode.notify import actions as notify_actions

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def async_set_gitpod_user_expiration(gitpoduser_id):
    logger.debug(f'Recalculate gitpoduser expiration for {gitpoduser_id}')
    return set_gitpod_user_expiration(gitpoduser_id) is not None


@shared_task
def async_add_to_organization(cohort_id, user_id):
    return add_to_organization(cohort_id, user_id)


@shared_task
def async_remove_from_organization(cohort_id, user_id, force=False):
    return remove_from_organization(cohort_id, user_id, force=force)


@shared_task
def async_accept_user_from_waiting_list(user_invite_id: int) -> None:
    from .models import UserInvite

    logger.debug(f'Process to accept UserInvite {user_invite_id}')

    if not (invite := UserInvite.objects.filter(id=user_invite_id).first()):
        logger.error(f'UserInvite {user_invite_id} not found')
        return

    if not invite.email:
        invite.status = 'ACCEPTED'
        invite.process_status = 'ERROR'
        invite.process_message = "Can't determine the user email"
        invite.save()
        return

    if user := User.objects.filter(email=invite.email).first():
        invite.status = 'ACCEPTED'
        invite.process_status = 'DONE'
        invite.process_message = f'User already exists with the id {user.id}'
        invite.save()
        return

    user = User(username=invite.email,
                email=invite.email,
                first_name=invite.first_name or '',
                last_name=invite.last_name or '')

    user.save()

    invite.user = user
    invite.status = 'ACCEPTED'
    invite.process_status = 'DONE'
    invite.process_message = f'Registered as User with id {user.id}'
    invite.save()

    notify_actions.send_email_message(
        'pick_password', user.email, {
            'SUBJECT': 'Set your password at 4Geeks',
            'LINK': os.getenv('API_URL', '') + f'/v1/auth/password/{invite.token}'
        })


@shared_task
def destroy_legacy_key(legacy_key_id):
    from .models import LegacyKey
    LegacyKey.objects.filter(id=legacy_key_id).delete()
