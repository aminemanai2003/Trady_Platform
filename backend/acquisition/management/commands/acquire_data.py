"""
Django management command to run data acquisition
Usage: python manage.py acquire_data [--source mt5|fred|news|all]
"""
from django.core.management.base import BaseCommand
from acquisition.orchestrator import run_full_acquisition
from acquisition.mt5_collector import collect_mt5_data
from acquisition.fred_collector import collect_fred_data
from acquisition.news_collector import collect_news_data


class Command(BaseCommand):
    help = 'Run data acquisition from various sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='all',
            choices=['all', 'mt5', 'fred', 'news'],
            help='Data source to acquire from'
        )

    def handle(self, *args, **options):
        source = options['source']
        
        self.stdout.write(self.style.SUCCESS(f'Starting data acquisition: {source}'))
        
        try:
            if source == 'all':
                run_full_acquisition()
            elif source == 'mt5':
                collect_mt5_data()
            elif source == 'fred':
                collect_fred_data()
            elif source == 'news':
                collect_news_data()
            
            self.stdout.write(self.style.SUCCESS('✅ Data acquisition completed successfully'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise
