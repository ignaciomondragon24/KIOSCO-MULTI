"""
Entry point for Railpack/Railway deployment.
Railpack auto-detects this file as the start command.
For production, use: gunicorn superrecord.wsgi
"""
import os
import subprocess
import sys


def main():
    """Run migrations, setup data, and start gunicorn."""
    port = os.environ.get('PORT', '8000')

    # Run migrations
    print("Running migrations...")
    subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], check=True)

    # Collect static files
    print("Collecting static files...")
    subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], check=False)

    # Setup initial data (superuser + roles + payment methods)
    print("Setting up initial data...")
    subprocess.run([sys.executable, 'manage.py', 'setup_initial_data'], check=False)

    # Start gunicorn
    print(f"Starting gunicorn on port {port}...")
    os.execvp('gunicorn', [
        'gunicorn',
        'superrecord.wsgi',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '2',
        '--threads', '2',
        '--worker-class', 'gthread',
        '--timeout', '120',
        '--log-file', '-',
        '--access-logfile', '-',
        '--error-logfile', '-',
    ])


if __name__ == '__main__':
    main()
