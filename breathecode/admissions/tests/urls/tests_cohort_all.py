"""
Test /cohort/all
"""
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from datetime import datetime
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import AdmissionsTestCase

class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_without_data(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_cohort_but_without_profile_academy(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        self.generate_models(authenticate=True, cohort=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_bad_get_academy(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_academy(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy={self.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_bad_get_location(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_location(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={self.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_false(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=false'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_true_without_current_data(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_true_with_current_data(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': f'{self.cohort.kickoff_date.isoformat()}Z',
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)