"""
Test /answer/:id
"""
from datetime import datetime
import io
import json
import random
import pytz
from django.utils import timezone
import pandas as pd
from pytz import UTC
from breathecode.provisioning.tasks import upload
from breathecode.provisioning import tasks
import re, string, os
import logging
from unittest.mock import PropertyMock, patch, MagicMock, call
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from random import choices

from breathecode.tests.mocks.requests import apply_requests_get_mock

from ..mixins import ProvisioningTestCase
from faker import Faker

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)

fake = Faker()
fake_url = fake.url()

UTC_NOW = timezone.now()

USERNAMES = [fake.slug() for _ in range(10)]
RANDOM_ACADEMIES = [random.randint(0, 2) for _ in range(10)]

while len(set(RANDOM_ACADEMIES[:3])) != 3:
    RANDOM_ACADEMIES = [random.randint(0, 2) for _ in range(10)]


def parse(s):
    return json.loads(s)


def repo_name(url):
    pattern = r'^https://github\.com/[^/]+/([^/]+)/'
    result = re.findall(pattern, url)
    return result[0]


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


def datetime_to_iso(date) -> str:
    return re.sub(r'\+00:00$', 'Z', date.replace(tzinfo=UTC).isoformat())


def datetime_to_show_date(date) -> str:
    return date.strftime('%Y-%m-%d')


def response_mock(status_code=200, content=[]):

    class Response():

        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content

        def json(self):
            return self.content

    return MagicMock(side_effect=[Response(status_code, x) for x in content])


def random_csv(lines=1):
    obj = {}

    for i in range(random.randint(1, 7)):
        obj[fake.slug()] = [fake.slug() for _ in range(lines)]

    return obj


def codespaces_csv(lines=1, data={}):
    usernames = [fake.slug() for _ in range(lines)]
    dates = [datetime_to_show_date(datetime.utcnow()) for _ in range(lines)]
    products = [fake.name() for _ in range(lines)]
    skus = [fake.slug() for _ in range(lines)]
    quantities = [random.randint(1, 10) for _ in range(lines)]
    unit_types = [fake.slug() for _ in range(lines)]
    price_per_units = [round(random.random() * 100, 6) for _ in range(lines)]
    multipliers = [round(random.random() * 100, 6) for _ in range(lines)]
    repository_slugs = [fake.slug() for _ in range(lines)]
    owners = [fake.slug() for _ in range(lines)]

    # dictionary of lists
    return {
        'Repository Slug': repository_slugs,
        'Username': usernames,
        'Date': dates,
        'Product': products,
        'SKU': skus,
        'Quantity': quantities,
        'Unit Type': unit_types,
        'Price Per Unit ($)': price_per_units,
        'Multiplier': multipliers,
        'Owner': owners,
        **data,
    }


def get_gitpod_metadata():
    username = fake.slug()
    repo = fake.slug()
    branch = fake.slug()
    return {
        'userName': username,
        'contextURL': f'https://github.com/{username}/{repo}/tree/{branch}/',
    }


def gitpod_csv(lines=1, data={}):
    ids = [random.randint(1, 10) for _ in range(lines)]
    credit_cents = [random.randint(1, 10000) for _ in range(lines)]
    effective_times = [datetime_to_iso(datetime.utcnow()) for _ in range(lines)]
    kinds = [fake.slug() for _ in range(lines)]

    metadata = [json.dumps(get_gitpod_metadata()) for _ in range(lines)]

    # dictionary of lists
    return {
        'id': ids,
        'creditCents': credit_cents,
        'effectiveTime': effective_times,
        'kind': kinds,
        'metadata': metadata,
        **data,
    }


def csv_file_mock(obj):
    df = pd.DataFrame.from_dict(obj)

    s_buf = io.StringIO()
    df.to_csv(s_buf)

    s_buf.seek(0)

    return s_buf.read().encode('utf-8')


def provisioning_activity_data(data={}):
    return {
        'bill_id': 1,
        'currency_code': 'USD',
        'id': 1,
        'multiplier': None,
        'notes': None,
        'price_per_unit': 38.810343970751504,
        'processed_at': ...,
        'product_name': 'Lori Cook',
        'quantity': 8.0,
        'registered_at': ...,
        'repository_url': 'https://github.com/answer-same-which/heart-bill-computer',
        'sku': 'point-yes-another',
        'status': 'PERSISTED',
        'status_text': '',
        'task_associated_slug': 'heart-bill-computer',
        'unit_type': 'eat-hold-member',
        'username': 'soldier-job-woman',
        **data,
    }


def provisioning_bill_data(data={}):
    return {
        'academy_id': 1,
        'currency_code': 'USD',
        'id': 1,
        'paid_at': None,
        'status': 'PENDING',
        'status_details': None,
        'total_amount': 0.0,
        'stripe_url': None,
        **data,
    }


def github_academy_user_data(data={}):
    return {
        'academy_id': 0,
        'id': 0,
        'storage_action': 'ADD',
        'storage_log': None,
        'storage_status': 'PENDING',
        'storage_synch_at': None,
        'user_id': None,
        'username': None,
        **data,
    }


class RandomFileTestSuite(ProvisioningTestCase):
    # When: random csv is uploaded and the file does not exists
    # Then: the task should not create any bill or activity
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=False),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_random_csv__file_does_not_exists(self):
        csv = random_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'File {slug} not found'),
        ])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # When: random csv is uploaded and the file exists
    # Then: the task should not create any bill or activity
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_random_csv__file_exists(self):
        csv = random_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'File {slug} has an unsupported origin or the provider had changed the file format'),
        ])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv and 1 ProvisioningBill
    # When: random csv is uploaded and the file exists
    # Then: the task should not create any bill or activity
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_random_csv__file_exists__already_processed(self):
        csv = random_csv(10)
        slug = self.bc.fake.slug()
        provisioning_bill = {'hash': slug}
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(f'File {slug} already processed'),
        ])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv and 1 ProvisioningBill
    # When: random csv is uploaded and the file exists
    # Then: the task should not create any bill or activity
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_random_csv__file_exists__already_processed__(self):
        csv = random_csv(10)
        slug = self.bc.fake.slug()
        provisioning_bill = {
            'hash': slug,
            'status': random.choice(['DISPUTED', 'IGNORED', 'PAID']),
        }
        model = self.bc.database.create(provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug, force=True)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('Cannot force upload because there are bills with status DISPUTED, IGNORED or PAID'),
        ])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])


class CodespacesTestSuite(ProvisioningTestCase):
    ...

    # Given: a csv with codespaces data
    # When: users does not exist and vendor not found
    # Then: the task should not create any bill or activity
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_users_not_found(self):
        csv = codespaces_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data({
                'id':
                n + 1,
                'hash':
                slug,
                'bill_id':
                None,
                'username':
                csv['Username'][n],
                'registered_at':
                datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                'product_name':
                csv['Product'][n],
                'sku':
                csv['SKU'][n],
                'quantity':
                float(csv['Quantity'][n]),
                'unit_type':
                csv['Unit Type'][n],
                'price_per_unit':
                csv['Price Per Unit ($)'][n],
                'currency_code':
                'USD',
                'multiplier':
                csv['Multiplier'][n],
                'repository_url':
                f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                'task_associated_slug':
                csv['Repository Slug'][n],
                'processed_at':
                UTC_NOW,
                'status':
                'ERROR',
                'status_text':
                ', '.join([
                    'Provisioning vendor Codespaces not found',
                    f"User {csv['Username'][n]} not found in any academy",
                ]),
            }) for n in range(10)
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])

        self.bc.check.calls(logging.Logger.error.call_args_list,
                            [call(f"Organization {csv['Owner'][n]} not found") for n in range(10)])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data, 20 AcademyAuthSettings, 20 Academy
    # When: users does not exist, vendor not found and
    #    -> each github organization have two AcademyAuthSettings
    # Then: the task should create 20 bills, 20 activities and two GithubAcademyUser per academy
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_users_not_found__case1(self):
        csv = codespaces_csv(10)

        academy_auth_settings = []

        id = 0
        for owner in csv['Owner']:
            academy_auth_settings.append({'github_username': owner, 'academy_id': id + 1})
            academy_auth_settings.append({'github_username': owner, 'academy_id': id + 2})
            id += 2

        self.bc.database.create(academy_auth_settings=academy_auth_settings, academy=20)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({
                'id': n + 1,
                'academy_id': n + 1,
                'hash': slug,
                'total_amount': 0.0,
            }) for n in range(20)
        ])

        id = 0
        activities = []
        for n in range(10):
            activities.append(
                provisioning_activity_data({
                    'id':
                    id + 1,
                    'hash':
                    slug,
                    'bill_id':
                    id + 1,
                    'username':
                    csv['Username'][n],
                    'registered_at':
                    datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name':
                    csv['Product'][n],
                    'sku':
                    csv['SKU'][n],
                    'quantity':
                    float(csv['Quantity'][n]),
                    'unit_type':
                    csv['Unit Type'][n],
                    'price_per_unit':
                    csv['Price Per Unit ($)'][n],
                    'currency_code':
                    'USD',
                    'multiplier':
                    csv['Multiplier'][n],
                    'repository_url':
                    f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug':
                    csv['Repository Slug'][n],
                    'processed_at':
                    UTC_NOW,
                    'status':
                    'ERROR',
                    'status_text':
                    ', '.join([
                        'Provisioning vendor Codespaces not found',
                    ]),
                }))

            activities.append(
                provisioning_activity_data({
                    'id':
                    id + 2,
                    'hash':
                    slug,
                    'bill_id':
                    id + 2,
                    'username':
                    csv['Username'][n],
                    'registered_at':
                    datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name':
                    csv['Product'][n],
                    'sku':
                    csv['SKU'][n],
                    'quantity':
                    float(csv['Quantity'][n]),
                    'unit_type':
                    csv['Unit Type'][n],
                    'price_per_unit':
                    csv['Price Per Unit ($)'][n],
                    'currency_code':
                    'USD',
                    'multiplier':
                    csv['Multiplier'][n],
                    'repository_url':
                    f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug':
                    csv['Repository Slug'][n],
                    'processed_at':
                    UTC_NOW,
                    'status':
                    'ERROR',
                    'status_text':
                    ', '.join([
                        'Provisioning vendor Codespaces not found',
                    ]),
                }))

            id += 2

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), activities)

        id = 0
        github_academy_users = []

        for n in range(10):
            github_academy_users.append(
                github_academy_user_data(
                    data={
                        'id': id + 1,
                        'academy_id': id + 1,
                        'storage_action': 'IGNORE',
                        'storage_status': 'PAYMENT_CONFLICT',
                        'username': csv['Username'][n],
                    }))

            github_academy_users.append(
                github_academy_user_data(
                    data={
                        'id': id + 2,
                        'academy_id': id + 2,
                        'storage_action': 'IGNORE',
                        'storage_status': 'PAYMENT_CONFLICT',
                        'username': csv['Username'][n],
                    }))

            id += 2

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), github_academy_users)

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data, 20 AcademyAuthSettings, 20 Academy
    # When: users does not exist, vendor not found and
    #    -> each github organization have two AcademyAuthSettings
    # Then: the task should create 20 bills, 20 activities and two GithubAcademyUser per academy
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_users_not_found__case2(self):
        csv = codespaces_csv(10)

        academy_auth_settings = []
        id = 0

        for owner in csv['Owner']:
            academy_auth_settings.append({'github_username': owner, 'academy_id': id + 1})
            academy_auth_settings.append({'github_username': owner, 'academy_id': id + 2})
            id += 2

        credentials_github = [{'username': csv['Username'][n], 'user_id': n + 1} for n in range(10)]
        self.bc.database.create(academy_auth_settings=academy_auth_settings,
                                academy=20,
                                user=10,
                                credentials_github=credentials_github)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({
                'id': n + 1,
                'academy_id': n + 1,
                'hash': slug,
                'total_amount': 0.0,
            }) for n in range(20)
        ])

        id = 0
        activities = []
        for n in range(10):
            activities.append(
                provisioning_activity_data({
                    'id':
                    id + 1,
                    'hash':
                    slug,
                    'bill_id':
                    id + 1,
                    'username':
                    csv['Username'][n],
                    'registered_at':
                    datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name':
                    csv['Product'][n],
                    'sku':
                    csv['SKU'][n],
                    'quantity':
                    float(csv['Quantity'][n]),
                    'unit_type':
                    csv['Unit Type'][n],
                    'price_per_unit':
                    csv['Price Per Unit ($)'][n],
                    'currency_code':
                    'USD',
                    'multiplier':
                    csv['Multiplier'][n],
                    'repository_url':
                    f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug':
                    csv['Repository Slug'][n],
                    'processed_at':
                    UTC_NOW,
                    'status':
                    'ERROR',
                    'status_text':
                    ', '.join([
                        'Provisioning vendor Codespaces not found',
                    ]),
                }))

            activities.append(
                provisioning_activity_data({
                    'id':
                    id + 2,
                    'hash':
                    slug,
                    'bill_id':
                    id + 2,
                    'username':
                    csv['Username'][n],
                    'registered_at':
                    datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name':
                    csv['Product'][n],
                    'sku':
                    csv['SKU'][n],
                    'quantity':
                    float(csv['Quantity'][n]),
                    'unit_type':
                    csv['Unit Type'][n],
                    'price_per_unit':
                    csv['Price Per Unit ($)'][n],
                    'currency_code':
                    'USD',
                    'multiplier':
                    csv['Multiplier'][n],
                    'repository_url':
                    f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug':
                    csv['Repository Slug'][n],
                    'processed_at':
                    UTC_NOW,
                    'status':
                    'ERROR',
                    'status_text':
                    ', '.join([
                        'Provisioning vendor Codespaces not found',
                    ]),
                }))

            id += 2

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), activities)

        id = 0
        github_academy_users = []

        for n in range(10):
            github_academy_users.append(
                github_academy_user_data(
                    data={
                        'id': id + 1,
                        'user_id': (id / 2) + 1,
                        'academy_id': id + 1,
                        'storage_action': 'IGNORE',
                        'storage_status': 'PAYMENT_CONFLICT',
                        'username': csv['Username'][n],
                    }))

            github_academy_users.append(
                github_academy_user_data(
                    data={
                        'id': id + 2,
                        'user_id': (id / 2) + 1,
                        'academy_id': id + 2,
                        'storage_action': 'IGNORE',
                        'storage_status': 'PAYMENT_CONFLICT',
                        'username': csv['Username'][n],
                    }))

            id += 2

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), github_academy_users)

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = codespaces_csv(10)

        github_academy_users = [{
            'username': x,
        } for x in csv['Username']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        provisioning_vendor = {'name': 'Codespaces'}
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 1,
                    'username': csv['Username'][n],
                    'registered_at': datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name': csv['Product'][n],
                    'sku': csv['SKU'][n],
                    'quantity': float(csv['Quantity'][n]),
                    'unit_type': csv['Unit Type'][n],
                    'price_per_unit': csv['Price Per Unit ($)'][n],
                    'currency_code': 'USD',
                    'multiplier': csv['Multiplier'][n],
                    'repository_url': f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug': csv['Repository Slug'][n],
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.assertEqual(
            self.bc.database.list_of('authenticate.GithubAcademyUser'),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog,
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, and the amount of rows is greater than the limit
    # Then: the task should create 1 bills and 10 activities
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    @patch('breathecode.provisioning.tasks.PANDAS_ROWS_LIMIT', PropertyMock(return_value=3))
    def test_pagination(self):
        csv = codespaces_csv(10)

        limit = tasks.PANDAS_ROWS_LIMIT
        tasks.PANDAS_ROWS_LIMIT = 3

        github_academy_users = [{
            'username': x,
        } for x in csv['Username']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        provisioning_vendor = {'name': 'Codespaces'}
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 1,
                    'username': csv['Username'][n],
                    'registered_at': datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name': csv['Product'][n],
                    'sku': csv['SKU'][n],
                    'quantity': float(csv['Quantity'][n]),
                    'unit_type': csv['Unit Type'][n],
                    'price_per_unit': csv['Price Per Unit ($)'][n],
                    'currency_code': 'USD',
                    'multiplier': csv['Multiplier'][n],
                    'repository_url': f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug': csv['Repository Slug'][n],
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.assertEqual(
            self.bc.database.list_of('authenticate.GithubAcademyUser'),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting upload for hash {slug}') for _ in range(4)])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [
            call(slug, 1),
            call(slug, 2),
            call(slug, 3),
        ])

        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

        tasks.PANDAS_ROWS_LIMIT = limit

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, force = True
    # Then: the task should create 1 bills and 10 activities
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything__force(self):
        csv = codespaces_csv(10)

        slug = self.bc.fake.slug()
        github_academy_users = [{
            'username': x,
        } for x in csv['Username']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        provisioning_vendor = {'name': 'Codespaces'}
        provisioning_bill = {'hash': slug}
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor,
                                        provisioning_bill=provisioning_bill)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug, force=True)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({
                'id': 2,
                'hash': slug
            }),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 2,
                    'username': csv['Username'][n],
                    'registered_at': datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name': csv['Product'][n],
                    'sku': csv['SKU'][n],
                    'quantity': float(csv['Quantity'][n]),
                    'unit_type': csv['Unit Type'][n],
                    'price_per_unit': csv['Price Per Unit ($)'][n],
                    'currency_code': 'USD',
                    'multiplier': csv['Multiplier'][n],
                    'repository_url': f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug': csv['Repository Slug'][n],
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.assertEqual(
            self.bc.database.list_of('authenticate.GithubAcademyUser'),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, GithubAcademyUser with PAYMENT_CONFLICT and IGNORE
    # Then: the task should create 1 bills and 10 activities
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything__case1(self):
        csv = codespaces_csv(10)

        github_academy_users = [{
            'username': x,
            'storage_status': 'PAYMENT_CONFLICT',
            'storage_action': 'IGNORE',
        } for x in csv['Username']]

        provisioning_vendor = {'name': 'Codespaces'}
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 1,
                    'username': csv['Username'][n],
                    'registered_at': datetime.strptime(csv['Date'][n], '%Y-%m-%d').replace(tzinfo=pytz.UTC),
                    'product_name': csv['Product'][n],
                    'sku': csv['SKU'][n],
                    'quantity': float(csv['Quantity'][n]),
                    'unit_type': csv['Unit Type'][n],
                    'price_per_unit': csv['Price Per Unit ($)'][n],
                    'currency_code': 'USD',
                    'multiplier': csv['Multiplier'][n],
                    'repository_url': f"https://github.com/{csv['Owner'][n]}/{csv['Repository Slug'][n]}",
                    'task_associated_slug': csv['Repository Slug'][n],
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.assertEqual(
            self.bc.database.list_of('authenticate.GithubAcademyUser'),
            self.bc.format.to_dict(model.github_academy_user),
        )

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])


class GitpodTestSuite(ProvisioningTestCase):

    # Given: a csv with codespaces data
    # When: users does not exist
    # Then: the task should not create any bill, create an activity with wrong status
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_users_not_found(self):
        csv = gitpod_csv(10)

        slug = self.bc.fake.slug()
        with patch('requests.get', response_mock(content=[{'id': 1} for _ in range(10)])):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [])
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data({
                'id':
                n + 1,
                'hash':
                slug,
                'bill_id':
                None,
                'username':
                parse(csv['metadata'][n])['userName'],
                'registered_at':
                self.bc.datetime.from_iso_string(csv['effectiveTime'][n]),
                'product_name':
                csv['kind'][n],
                'sku':
                str(csv['id'][n]),
                'quantity':
                float(csv['creditCents'][n]),
                'unit_type':
                'Credit cents',
                'price_per_unit':
                0.00036,
                'currency_code':
                'USD',
                'repository_url':
                parse(csv['metadata'][n])['contextURL'],
                'task_associated_slug':
                repo_name(parse(csv['metadata'][n])['contextURL']),
                'processed_at':
                UTC_NOW,
                'status':
                'ERROR',
                'status_text':
                ', '.join([
                    f"User {parse(csv['metadata'][n])['userName']} not found in any academy",
                    'Provisioning vendor Codespaces not found'
                ]),
            }) for n in range(10)
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'), [])

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser and 10 GithubAcademyUserLog
    # When: vendor not found
    # Then: the task should not create any bill or activity
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__vendor_not_found(self):
        csv = gitpod_csv(10)

        github_academy_users = [{
            'username': parse(x)['userName'],
        } for x in csv['metadata']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 1,
                    'username': parse(csv['metadata'][n])['userName'],
                    'registered_at': self.bc.datetime.from_iso_string(csv['effectiveTime'][n]),
                    'product_name': csv['kind'][n],
                    'sku': str(csv['id'][n]),
                    'quantity': float(csv['creditCents'][n]),
                    'unit_type': 'Credit cents',
                    'price_per_unit': 0.00036,
                    'currency_code': 'USD',
                    'repository_url': parse(csv['metadata'][n])['contextURL'],
                    'task_associated_slug': repo_name(parse(csv['metadata'][n])['contextURL']),
                    'processed_at': UTC_NOW,
                    'status': 'ERROR',
                    'status_text': ', '.join(['Provisioning vendor Codespaces not found']),
                }) for n in range(10)
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'),
                         self.bc.format.to_dict(model.github_academy_user))

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct
    # Then: the task should create 1 bills and 10 activities
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything(self):
        csv = gitpod_csv(10)

        github_academy_users = [{
            'username': parse(x)['userName'],
        } for x in csv['metadata']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        provisioning_vendor = {'name': 'Codespaces'}
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 1,
                    'username': parse(csv['metadata'][n])['userName'],
                    'registered_at': self.bc.datetime.from_iso_string(csv['effectiveTime'][n]),
                    'product_name': csv['kind'][n],
                    'sku': str(csv['id'][n]),
                    'quantity': float(csv['creditCents'][n]),
                    'unit_type': 'Credit cents',
                    'price_per_unit': 0.00036,
                    'currency_code': 'USD',
                    'repository_url': parse(csv['metadata'][n])['contextURL'],
                    'task_associated_slug': repo_name(parse(csv['metadata'][n])['contextURL']),
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'),
                         self.bc.format.to_dict(model.github_academy_user))

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, and the amount of rows is greater than the limit
    # Then: the task should create 1 bills and 10 activities
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    @patch('breathecode.provisioning.tasks.PANDAS_ROWS_LIMIT', PropertyMock(return_value=3))
    def test_pagination(self):
        csv = gitpod_csv(10)

        limit = tasks.PANDAS_ROWS_LIMIT
        tasks.PANDAS_ROWS_LIMIT = 3

        provisioning_vendor = {'name': 'Codespaces'}
        github_academy_users = [{
            'username': parse(x)['userName'],
        } for x in csv['metadata']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        model = self.bc.database.create(user=10,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({'hash': slug}),
        ])

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [
            provisioning_activity_data(
                {
                    'id': n + 1,
                    'hash': slug,
                    'bill_id': 1,
                    'username': parse(csv['metadata'][n])['userName'],
                    'registered_at': self.bc.datetime.from_iso_string(csv['effectiveTime'][n]),
                    'product_name': csv['kind'][n],
                    'sku': str(csv['id'][n]),
                    'quantity': float(csv['creditCents'][n]),
                    'unit_type': 'Credit cents',
                    'price_per_unit': 0.00036,
                    'currency_code': 'USD',
                    'repository_url': parse(csv['metadata'][n])['contextURL'],
                    'task_associated_slug': repo_name(parse(csv['metadata'][n])['contextURL']),
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                }) for n in range(10)
        ])

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'),
                         self.bc.format.to_dict(model.github_academy_user))

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Starting upload for hash {slug}') for _ in range(4)])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [
            call(slug, 1),
            call(slug, 2),
            call(slug, 3),
        ])

        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

        tasks.PANDAS_ROWS_LIMIT = limit

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, without ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per academy
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_from_github_credentials__generate_anything__case1(self):
        csv = gitpod_csv(10)

        github_academy_users = [{
            'username': parse(x)['userName'],
        } for x in csv['metadata']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        provisioning_vendor = {'name': 'Codespaces'}

        model = self.bc.database.create(user=10,
                                        academy=3,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()
        with patch('breathecode.services.google_cloud.File.download',
                   MagicMock(return_value=csv_file_mock(csv))):

            upload(slug)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({
                'id': 1,
                'academy_id': 1,
                'hash': slug,
            }),
            provisioning_bill_data({
                'id': 2,
                'academy_id': 2,
                'hash': slug,
            }),
            provisioning_bill_data({
                'id': 3,
                'academy_id': 3,
                'hash': slug,
            }),
        ])

        activities = []
        id = 0
        for n1 in range(10):
            for n2 in range(3):
                id += 1
                activities.append({
                    'id': id,
                    'hash': slug,
                    'bill_id': n2 + 1,
                    'username': parse(csv['metadata'][n1])['userName'],
                    'registered_at': self.bc.datetime.from_iso_string(csv['effectiveTime'][n1]),
                    'product_name': csv['kind'][n1],
                    'sku': str(csv['id'][n1]),
                    'quantity': float(csv['creditCents'][n1]),
                    'unit_type': 'Credit cents',
                    'price_per_unit': 0.00036,
                    'currency_code': 'USD',
                    'repository_url': parse(csv['metadata'][n1])['contextURL'],
                    'task_associated_slug': repo_name(parse(csv['metadata'][n1])['contextURL']),
                    'processed_at': UTC_NOW,
                    'status': 'PERSISTED',
                    'status_text': '',
                    'multiplier': None,
                    'notes': None,
                })

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), activities)

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'),
                         self.bc.format.to_dict(model.github_academy_user))

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])

    # Given: a csv with codespaces data and 10 User, 10 GithubAcademyUser, 10 GithubAcademyUserLog
    #     -> and 1 ProvisioningVendor of type codespaces
    # When: all the data is correct, with ProfileAcademy
    # Then: the task should create 1 bills and 10 activities per user's ProfileAcademy
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple(
        'breathecode.services.google_cloud.File',
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        upload=MagicMock(),
        exists=MagicMock(return_value=True),
        url=MagicMock(return_value='https://storage.cloud.google.com/media-breathecode/hardcoded_url'),
        create=True)
    @patch('breathecode.provisioning.tasks.upload.delay', MagicMock(wraps=upload.delay))
    @patch('breathecode.provisioning.tasks.calculate_bill_amounts.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    @patch('breathecode.authenticate.signals.academy_invite_accepted.send', MagicMock())
    def test_from_github_credentials__generate_anything__case2(self):
        csv = gitpod_csv(10)

        github_academy_users = [{
            'username': parse(x)['userName'],
        } for x in csv['metadata']]
        github_academy_user_logs = [{
            'storage_status': 'SYNCHED',
            'storage_action': 'ADD',
            'academy_user_id': n + 1,
        } for n in range(10)]
        provisioning_vendor = {'name': 'Codespaces'}
        profile_academies = []

        for user_n in range(10):
            for academy_n in range(3):
                profile_academies.append({
                    'academy_id': academy_n + 1,
                    'user_id': user_n + 1,
                    'status': 'ACTIVE',
                })

        credentials_github = [{
            'username': parse(csv['metadata'][n])['userName'],
            'user_id': n + 1,
        } for n in range(10)]

        model = self.bc.database.create(user=10,
                                        credentials_github=credentials_github,
                                        academy=3,
                                        profile_academy=profile_academies,
                                        github_academy_user=github_academy_users,
                                        github_academy_user_log=github_academy_user_logs,
                                        provisioning_vendor=provisioning_vendor)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        slug = self.bc.fake.slug()

        y = [[model.academy[RANDOM_ACADEMIES[x]]] for x in range(10)]

        with patch('random.choices', MagicMock(side_effect=y)):
            with patch('breathecode.services.google_cloud.File.download',
                       MagicMock(return_value=csv_file_mock(csv))):

                upload(slug)

        academies = []

        for n in RANDOM_ACADEMIES:
            if n not in academies:
                academies.append(n)

        academies = list(academies)

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            provisioning_bill_data({
                'id': 1,
                'academy_id': academies[0] + 1,
                'hash': slug,
            }),
            provisioning_bill_data({
                'id': 2,
                'academy_id': academies[1] + 1,
                'hash': slug,
            }),
            provisioning_bill_data({
                'id': 3,
                'academy_id': academies[2] + 1,
                'hash': slug,
            }),
        ])

        mapping = {}

        for n in range(3):
            mapping[academies[n]] = n + 1

        activities = []
        id = 0
        for n1 in range(10):
            id += 1
            activities.append({
                'id': id,
                'hash': slug,
                'bill_id': mapping[RANDOM_ACADEMIES[n1]],
                'username': parse(csv['metadata'][n1])['userName'],
                'registered_at': self.bc.datetime.from_iso_string(csv['effectiveTime'][n1]),
                'product_name': csv['kind'][n1],
                'sku': str(csv['id'][n1]),
                'quantity': float(csv['creditCents'][n1]),
                'unit_type': 'Credit cents',
                'price_per_unit': 0.00036,
                'currency_code': 'USD',
                'repository_url': parse(csv['metadata'][n1])['contextURL'],
                'task_associated_slug': repo_name(parse(csv['metadata'][n1])['contextURL']),
                'processed_at': UTC_NOW,
                'status': 'PERSISTED',
                'status_text': '',
                'multiplier': None,
                'notes': None,
            })

        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), activities)

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUser'),
                         self.bc.format.to_dict(model.github_academy_user))

        self.bc.check.calls(logging.Logger.info.call_args_list, [call(f'Starting upload for hash {slug}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(tasks.upload.delay.call_args_list, [])
        self.bc.check.calls(tasks.calculate_bill_amounts.delay.call_args_list, [call(slug)])
