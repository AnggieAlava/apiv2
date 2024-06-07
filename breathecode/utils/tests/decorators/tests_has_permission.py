import json
from datetime import timedelta
from functools import wraps
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

import breathecode.utils.decorators as decorators
from breathecode.payments import models
from breathecode.payments import signals as payments_signals
from breathecode.utils.decorators import ServiceContext

from ..mixins import UtilsTestCase

PERMISSION = 'can_kill_kenny'
GET_RESPONSE = {'a': 1}
GET_ID_RESPONSE = {'a': 2}
POST_RESPONSE = {'a': 3}
PUT_ID_RESPONSE = {'a': 4}
DELETE_ID_RESPONSE = {'a': 5}
UTC_NOW = timezone.now()


def build_view_function(methods,
                        data,
                        decorator,
                        decorator_args=(),
                        decorator_kwargs={},
                        with_permission=False,
                        with_id=False):

    @api_view(methods)
    @permission_classes([AllowAny])
    @decorator(*decorator_args, **decorator_kwargs)
    def view_function(request, *args, **kwargs):
        if with_permission:
            assert kwargs['permission'] == PERMISSION
            assert args[0] == PERMISSION

        if with_id:
            assert kwargs['id'] == 1

        return Response(data)

    return view_function


get = build_view_function(['GET'], GET_RESPONSE, decorators.has_permission, decorator_args=(PERMISSION, ))

get_id = build_view_function(['GET'],
                             GET_ID_RESPONSE,
                             decorators.has_permission,
                             decorator_args=(PERMISSION, ),
                             with_id=True)

post = build_view_function(['POST'], POST_RESPONSE, decorators.has_permission, decorator_args=(PERMISSION, ))

put_id = build_view_function(['PUT'],
                             PUT_ID_RESPONSE,
                             decorators.has_permission,
                             decorator_args=(PERMISSION, ),
                             with_id=True)

delete_id = build_view_function(['DELETE'],
                                DELETE_ID_RESPONSE,
                                decorators.has_permission,
                                decorator_args=(PERMISSION, ),
                                with_id=True)


def build_view_class(decorator, decorator_args=(), decorator_kwargs={}, with_permission=False):

    class CustomView(APIView):
        """
        List all snippets, or create a new snippet.
        """
        permission_classes = [AllowAny]

        @staticmethod
        def decorate(func):

            def wrapper(request, *args, **kwargs):
                if with_permission:
                    assert kwargs.get('permission') == PERMISSION
                    assert args[0] == PERMISSION

                return func(request, *args, **kwargs)

            return decorator(*decorator_args, **decorator_kwargs)(wrapper)

        def get(self, request, *args, **kwargs):
            if 'id' in kwargs:
                assert kwargs['id'] == 1
                return Response(GET_ID_RESPONSE)
            return Response(GET_RESPONSE)

        get = decorate(get)

        def post(self, request, *args, **kwargs):
            return Response(POST_RESPONSE)

        post = decorate(post)

        def put(self, request, *args, **kwargs):
            if 'id' not in kwargs:
                assert 0
            assert kwargs['id'] == 1
            return Response(PUT_ID_RESPONSE)

        put = decorate(put)

        def delete(self, request, *args, **kwargs):
            if 'id' not in kwargs:
                assert 0
            assert kwargs['id'] == 1
            return Response(DELETE_ID_RESPONSE)

        delete = decorate(delete)

    CustomView.__test__ = False

    return CustomView


TestView = build_view_class(decorators.has_permission, decorator_args=(PERMISSION, ))


class FunctionBasedViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 Function get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')

        view = post

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])


class ViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 View get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__anonymous_user(self):
        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])
