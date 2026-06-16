"""
Django management command to run data preparation pipeline
Usage: python manage.py prepare_data [--step explore|clean|feature|validate|all]
"""
from django.core.management.base import BaseCommand
from preparation.scripts.explore_data import explore_data
from preparation.scripts.clean_data import clean_data
from preparation.scripts.engineer_features import engineer_features
from preparation.scripts.validate_data import validate_data


class Command(BaseCommand):
    help = 'Run data preparation pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--step',
            type=str,
            default='all',
            choices=['all', 'explore', 'clean', 'feature', 'validate'],
            help='Preparation step to run'
        )

    def handle(self, *args, **options):
        step = options['step']
        
        self.stdout.write(self.style.SUCCESS(f'Starting data preparation: {step}'))
        
        try:
            if step in ['all', 'explore']:
                self.stdout.write('📊 Exploring data...')
                explore_data()
            
            if step in ['all', 'clean']:
                self.stdout.write('🧹 Cleaning data...')
                clean_data()
            
            if step in ['all', 'feature']:
                self.stdout.write('⚙️ Engineering features...')
                engineer_features()
            
            if step in ['all', 'validate']:
                self.stdout.write('✅ Validating data...')
                validate_data()
            
            self.stdout.write(self.style.SUCCESS('✅ Data preparation completed successfully'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise
