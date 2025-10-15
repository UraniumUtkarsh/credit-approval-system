# credit_system/management/commands/ingest_data.py
from django.core.management.base import BaseCommand
from credit_system.tasks import ingest_initial_data

class Command(BaseCommand):
    help = 'Triggers the Celery task to ingest initial customer and loan data.'

    def handle(self, *args, **options):
        self.stdout.write("Sending data ingestion task to Celery...")
        # Use .delay() to send it to the background worker
        ingest_initial_data.delay() 
        self.stdout.write(self.style.SUCCESS('Task sent successfully! Check worker logs for status.'))