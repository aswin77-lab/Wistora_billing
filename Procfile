web: sh -c "python core/manage.py migrate && python core/manage.py create_default_users && gunicorn --chdir core core.wsgi:application"
