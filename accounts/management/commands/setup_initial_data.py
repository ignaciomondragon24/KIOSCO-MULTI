"""
Management Command for Railway deployment setup.
Creates superuser from environment variables and initializes default data.
Safe to run multiple times (idempotent).
"""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup initial data for deployment (superuser + default data). Safe to run multiple times.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('CHE GOLOSO - Setup Inicial'))
        self.stdout.write('')

        # 1. Create superuser from environment variables
        self._create_superuser()

        # 2. Initialize default data (roles, payment methods, etc.)
        self._init_default_data()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('[OK] Setup inicial completado exitosamente'))

    def _create_superuser(self):
        """Create superuser from environment variables if it doesn't exist."""
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', '')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    '[WARN]DJANGO_SUPERUSER_USERNAME y/o DJANGO_SUPERUSER_PASSWORD no configurados. '
                    'Saltando creación de superusuario.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'  [INFO]Superusuario "{username}" ya existe. Sin cambios.')
            return

        try:
            User.objects.create_superuser(
                username=username,
                email=email or None,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS(f'  [OK] Superusuario "{username}" creado exitosamente')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  [ERROR] Error creando superusuario: {e}')
            )

    def _init_default_data(self):
        """Run init_data command to create roles, payment methods, etc."""
        try:
            self.stdout.write('  Inicializando datos por defecto...')
            call_command('init_data', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  [OK] Datos por defecto inicializados'))
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  [WARN]Error en init_data (no crítico): {e}')
            )
