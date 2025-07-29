from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Booking

class Command(BaseCommand):
    help = 'Mark bookings as completed after their check-out date'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find confirmed bookings that have passed their checkout date
        completed_bookings = Booking.objects.filter(
            status='confirmed',
            check_out__lt=today
        )
        
        count = completed_bookings.count()
        
        if count > 0:
            completed_bookings.update(status='completed')
            self.stdout.write(
                self.style.SUCCESS(f'Successfully marked {count} booking(s) as completed')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No bookings to mark as completed')
            )
