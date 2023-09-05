from unittest.mock import MagicMock, call, patch
from rest_framework import status

from breathecode.utils.validation_exception import ValidationException
from ..mixins import MarketingTestCase


class LeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 CohortUser without educational_status ACTIVE
    """

    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    @patch('logging.Logger.warn', MagicMock())
    def test_cohort_saved__create__without_educational_status_active(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student
        import logging

        with self.assertRaisesMessage(ValidationException, 'user-not-found-in-org'):
            model = self.generate_models(cohort_user=True)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                'cohort_id': 1,
                'educational_status': None,
                'finantial_status': 'ACTIVE',
                'history_log': {},
                'id': 1,
                'role': 'STUDENT',
                'user_id': 1,
                'watching': False,
            },
        ])
        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [])
        self.assertEqual(logging.Logger.warn.call_args_list, [])

    """
    🔽🔽🔽 CohortUser with status ACTIVE
    """

    @patch('breathecode.marketing.tasks.add_cohort_task_to_student.delay', MagicMock())
    @patch('logging.Logger.warn', MagicMock())
    def test_cohort_saved__create__with_educational_status_active(self):
        from breathecode.marketing.tasks import add_cohort_task_to_student
        import logging

        cohort_user_kwargs = {'educational_status': 'ACTIVE'}
        model = self.generate_models(cohort_user=True, cohort_user_kwargs=cohort_user_kwargs)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'),
                         [self.model_to_dict(model, 'cohort_user')])
        self.assertEqual(add_cohort_task_to_student.delay.call_args_list, [
            call(model.user.id, model.cohort.id, model.cohort.academy.id),
        ])
        self.assertEqual(logging.Logger.warn.call_args_list, [
            call(f'Student is now active in cohort `{model.cohort.slug}`, processing task'),
        ])
