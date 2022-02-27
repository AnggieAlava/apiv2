from unittest.mock import patch, MagicMock, call
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.jobs.models import Spider
from breathecode.jobs.admin import fetch_sync_all_data_admin
from ..mixins import JobsTestCase
from django.http.request import HttpRequest


class RunSpiderAdminTestSuite(JobsTestCase):
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('django.contrib.messages.add_message', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.jobs.actions.fetch_sync_all_data',
           MagicMock(side_effect=Exception('They killed kenny')))
    def test_fetch_sync_all_data_admin__with_zero_spider_logger_error(self):
        from breathecode.jobs.actions import fetch_sync_all_data
        from logging import Logger

        model = self.bc.database.create(spider=1)
        request = HttpRequest()
        queryset = Spider.objects.all()

        fetch_sync_all_data_admin(None, request, queryset)
        self.assertEqual(Logger.error.call_args_list,
                         [call('There was an error retriving the spider They killed kenny')])

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('django.contrib.messages.add_message', MagicMock())
    @patch('breathecode.jobs.actions.fetch_sync_all_data', MagicMock())
    def test_fetch_sync_all_data_admin__with_zero_spider(self):
        from breathecode.jobs.actions import fetch_sync_all_data
        request = HttpRequest()
        queryset = Spider.objects.all()

        fetch_sync_all_data_admin(None, request, queryset)

        self.assertEqual(fetch_sync_all_data.call_args_list, [])

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('breathecode.jobs.actions.fetch_sync_all_data', MagicMock())
    def test_fetch_sync_all_data_admin__with_one_spider(self):
        from breathecode.jobs.actions import fetch_sync_all_data
        from django.contrib import messages

        model = self.bc.database.create(spider=True)

        request = HttpRequest()
        queryset = Spider.objects.all()

        fetch_sync_all_data_admin(None, request, queryset)

        self.assertEqual(fetch_sync_all_data.call_args_list, [call(model.spider)])

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('breathecode.jobs.actions.fetch_sync_all_data', MagicMock())
    def test_fetch_sync_all_data_admin__with_two_spiders(self):
        from breathecode.jobs.actions import fetch_sync_all_data
        from django.contrib import messages

        model_1 = self.bc.database.create(spider=1)
        model_2 = self.bc.database.create(spider=1)

        request = HttpRequest()
        queryset = Spider.objects.all()

        fetch_sync_all_data_admin(None, request, queryset)

        self.assertEqual(fetch_sync_all_data.call_args_list, [call(model_1.spider), call(model_2.spider)])
