from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tickets.models import Order
from tickets.paystack import verify_transaction
from tickets.services import complete_purchase


class Command(BaseCommand):
    help = 'Reconcile pending orders that missed the webhook'

    def handle(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(minutes=5)

        pending_orders = Order.objects.filter(
            status=Order.Status.PENDING,
            created_at__lte=cutoff,
        ).select_related('buyer', 'event', 'ticket_type')

        if not pending_orders.exists():
            self.stdout.write('No pending orders to reconcile.')
            return

        self.stdout.write(f'Found {pending_orders.count()} pending order(s).')

        completed = 0
        failed = 0

        for order in pending_orders:
            try:
                result = verify_transaction(str(order.id))
                if result['status'] == 'success':
                    complete_purchase(order=order)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Completed order {order.id} for {order.buyer.username}'
                        )
                    )
                    completed += 1
                else:
                    # Payment failed or was abandoned — mark order as failed
                    order.status = Order.Status.FAILED
                    order.save(update_fields=['status'])
                    self.stdout.write(
                        f'Marked order {order.id} as failed '
                        f'(Paystack status: {result["status"]})'
                    )
                    failed += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing order {order.id}: {e}')
                )

        self.stdout.write(
            f'Done. Completed: {completed}, Failed: {failed}'
        )
        
'''
CRON JOB:
Schedule: */5 * * * *
Command:  python manage.py reconcile_orders
'''