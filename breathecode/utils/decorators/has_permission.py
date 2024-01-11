import re
from datetime import datetime, timedelta
import logging
import traceback
from typing import Callable, Optional, TypedDict

from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.views import APIView
from django.db.models import Sum
from django.shortcuts import render
from django.http import JsonResponse

from breathecode.authenticate.models import Permission, User
from breathecode.payments.signals import consume_service

from ..exceptions import ProgrammingError
from ..payment_exception import PaymentException
from ..validation_exception import ValidationException
from rest_framework.response import Response

__all__ = ['has_permission', 'validate_permission', 'HasPermissionCallback', 'PermissionContextType']

logger = logging.getLogger(__name__)


class PermissionContextType(TypedDict):
    utc_now: datetime
    consumer: bool
    permission: str
    request: WSGIRequest
    consumables: QuerySet
    time_of_life: Optional[timedelta]
    will_consume: bool
    is_consumption_session: bool


HasPermissionCallback = Callable[[PermissionContextType, tuple, dict], tuple[PermissionContextType, tuple,
                                                                             dict, Optional[timedelta]]]


def validate_permission(user: User, permission: str, consumer: bool | HasPermissionCallback = False) -> bool:
    if consumer:
        return User.objects.filter(id=user.id, groups__permissions__codename=permission).exists()

    found = Permission.objects.filter(codename=permission).first()
    if not found:
        return False

    return found.user_set.filter(id=user.id).exists() or found.group_set.filter(user__id=user.id).exists()


def render_message(r,
                   msg,
                   btn_label=None,
                   btn_url=None,
                   btn_target='_blank',
                   data=None,
                   status=None,
                   go_back=None,
                   url_back=None):
    if data is None:
        data = {}

    _data = {
        'MESSAGE': msg,
        'BUTTON': btn_label,
        'BUTTON_TARGET': btn_target,
        'LINK': btn_url,
        'GO_BACK': go_back,
        'URL_BACK': url_back
    }

    return render(r, 'message.html', {**_data, **data}, status=status)


def has_permission(permission: str,
                   consumer: bool | HasPermissionCallback = False,
                   format='json') -> callable:
    """This decorator check if the current user can access to the resource through of permissions"""

    from breathecode.payments.models import Consumable, ConsumptionSession

    def decorator(function: callable) -> callable:

        def wrapper(*args, **kwargs):

            def build_context(**opts):
                return {
                    'utc_now': utc_now,
                    'consumer': consumer,
                    'permission': permission,
                    'request': request,
                    'consumables': Consumable.objects.none(),
                    'time_of_life': None,
                    'will_consume': True,
                    'is_consumption_session': False,
                    **opts,
                }

            if isinstance(permission, str) == False:
                raise ProgrammingError('Permission must be a string')

            try:
                if hasattr(args[0], '__class__') and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], 'user') and hasattr(args[0].user, 'has_perm'):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgrammingError('Missing request information, use this decorator with DRF View')

            try:
                utc_now = timezone.now()
                session = ConsumptionSession.get_session(request)
                if session:
                    if callable(consumer):
                        context = build_context(is_consumption_session=True)
                        context, args, kwargs = consumer(context, args, kwargs)

                    return function(*args, **kwargs)

                if validate_permission(request.user, permission, consumer):
                    context = build_context()

                    if consumer:
                        items = Consumable.list(user=request.user, permission=permission)
                        context['consumables'] = items

                    if callable(consumer):
                        context, args, kwargs = consumer(context, args, kwargs)

                    if consumer and context['time_of_life']:
                        consumables = context['consumables']
                        for item in consumables.filter(consumptionsession__status='PENDING').exclude(
                                how_many=0):

                            sum = item.consumptionsession_set.filter(status='PENDING').aggregate(
                                Sum('how_many'))

                            if item.how_many - sum['how_many__sum'] == 0:
                                context['consumables'] = context['consumables'].exclude(id=item.id)

                    if consumer and context['will_consume'] and not context['consumables']:
                        raise PaymentException(
                            f'You do not have enough credits to access this service: {permission}',
                            slug='with-consumer-not-enough-consumables')

                    if consumer and context['will_consume'] and context['time_of_life'] and (
                            consumable := context['consumables'].first()):
                        session = ConsumptionSession.build_session(request, consumable,
                                                                   context['time_of_life'])

                    response = function(*args, **kwargs)

                    it_will_consume = context['will_consume'] and consumer and response.status_code < 400
                    if it_will_consume and session:
                        session.will_consume(1)

                    elif it_will_consume:
                        item = context['consumables'].first()
                        consume_service.send(instance=item, sender=item.__class__, how_many=1)

                    return response

                elif not consumer and isinstance(request.user, AnonymousUser):
                    raise ValidationException(f'Anonymous user don\'t have this permission: {permission}',
                                              code=403,
                                              slug='anonymous-user-without-permission')

                elif not consumer:
                    raise ValidationException((f'You (user: {request.user.id}) don\'t have this permission: '
                                               f'{permission}'),
                                              code=403,
                                              slug='without-permission')

                elif consumer and isinstance(request.user, AnonymousUser):
                    raise PaymentException(
                        f'Anonymous user do not have enough credits to access this service: {permission}',
                        slug='anonymous-user-not-enough-consumables')

                else:
                    raise PaymentException(
                        f'You do not have enough credits to access this service: {permission}',
                        slug='not-enough-consumables')

            # handle html views errors
            except PaymentException as e:
                if format == 'websocket':
                    raise e

                if format == 'html':
                    from breathecode.payments.models import Subscription, PlanOffer, PlanFinancing

                    context = build_context()
                    context, args, kwargs = consumer(context, args, kwargs)

                    print('context')
                    print(context)
                    print('context[consumer]')
                    print(context['consumer'])

                    renovate_consumables = {}
                    url = request.path
                    match = re.search(r'service/(.*)', url)
                    service = match.group(1)

                    subscription = Subscription.objects.filter(
                        user=request.user,
                        plans__mentorship_service_set__mentorship_services__slug=service).first()

                    plan_offer = None
                    user_plans = []

                    if subscription is not None:
                        user_plans = subscription.plans.all()
                    else:
                        plan_financing = PlanFinancing.objects.filter(
                            user=request.user,
                            plans__mentorship_service_set__mentorship_services__slug=service).first()
                        if plan_financing is not None:
                            user_plans = plan_financing.plans.all()

                    for plan in user_plans:
                        plan_offer = PlanOffer.objects.filter(original_plan__slug=plan.slug).first()

                    if plan_offer is not None:
                        renovate_consumables['btn_label'] = 'Get more consumables'
                        renovate_consumables[
                            'btn_url'] = f'https://4geeks.com/checkout?plan={plan_offer.suggested_plan.slug}'
                    elif subscription is not None:
                        current_plan = user_plans.filter(
                            mentorship_service_set__mentorship_services__slug=service).first()
                        renovate_consumables['btn_label'] = 'Get more consumables'
                        renovate_consumables[
                            'btn_url'] = f'https://4geeks.com/checkout?mentorship_service_set={current_plan.mentorship_service_set.slug}'

                    return render_message(request,
                                          str(e),
                                          status=402,
                                          go_back='Go back to Dashboard',
                                          url_back='https://4geeks.com/choose-program',
                                          **renovate_consumables)

                return Response({'detail': str(e), 'status_code': 402}, 402)

            # handle html views errors
            except ValidationException as e:
                if format == 'websocket':
                    raise e

                status = e.status_code if hasattr(e, 'status_code') else 400

                if format == 'html':
                    return render_message(request, str(e), status=status)

                return Response({'detail': str(e), 'status_code': status}, status)

            # handle html views errors
            except Exception as e:
                # show stacktrace for unexpected exceptions
                traceback.print_exc()

                if format == 'html':
                    return render_message(request,
                                          'unexpected error, contact admin if you are affected',
                                          status=500)

                response = JsonResponse({'detail': str(e), 'status_code': 500})
                response.status_code = 500
                return response

        return wrapper

    return decorator
