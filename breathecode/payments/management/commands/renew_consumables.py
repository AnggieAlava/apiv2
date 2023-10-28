from datetime import timedelta
from django.core.management.base import BaseCommand
from ...models import ServiceStockScheduler, Subscription
from django.utils import timezone

from ... import tasks


# renew the credits every 1 hours
class Command(BaseCommand):
    help = 'Renew credits'

    def handle(self, *args, **options):
        utc_now = timezone.now()
        subscriptions = Subscription.objects.filter().exclude(status='CANCELLED').exclude(status='DEPRECATED')

        subscription_ids = list(subscriptions.values_list('id', flat=True))

        no_need_to_renew = ServiceStockScheduler.objects.filter(
            consumables__valid_until__gte=utc_now +
            timedelta(hours=2)).exclude(subscription__status='CANCELLED').exclude(
                subscription__status='DEPRECATED').exclude(subscription__status='PAYMENT_ISSUE')

        for subscription in no_need_to_renew:
            subscription_ids.remove(subscription.id)

        for subscription_id in subscription_ids:
            tasks.renew_consumables.delay(subscription_id)
