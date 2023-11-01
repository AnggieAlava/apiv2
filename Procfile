release: export CORALOGIX_SUBSYSTEM=release; python manage.py migrate && python manage.py create_academy_roles && python manage.py set_permissions
celeryworker: export CORALOGIX_SUBSYSTEM=celeryworker; export CELERY_WORKER_RUNNING=True; export REMAP_SIGTERM=SIGQUIT; newrelic-admin run-program bin/start-pgbouncer-stunnel celery -A breathecode.celery worker --loglevel=INFO --concurrency 1 --prefetch-multiplier=4 --max-tasks-per-child=500
web: export CORALOGIX_SUBSYSTEM=web; newrelic-admin run-program bin/start-pgbouncer-stunnel gunicorn breathecode.wsgi --timeout 29 --workers $WEB_WORKERS --worker-connections $WEB_WORKER_CONNECTION --worker-class $WEB_WORKER_CLASS
