if [ -n "$SPACE_ID" ]; then
    PORT=${PORT:-7860}
    export DEBUG=False
else
    PORT=${PORT:-8000}
fi

uv run manage.py collectstatic --noinput
uv run manage.py makemigrations
uv run manage.py migrate --noinput
uv run python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if 'app_project' in table_names:
            columns = [col.name for col in connection.introspection.get_table_description(cursor, 'app_project')]
            if 'is_community' not in columns:
                cursor.execute('ALTER TABLE app_project ADD COLUMN is_community bool NOT NULL DEFAULT 0;')
                print('Auto-migrated app_project table: added is_community column.')
except Exception as e:
    print('Schema check warning:', e)
"
uv run manage.py loaddata units superuser_poshak
uv run uwsgi --ini uwsgi.ini --http-socket :$PORT
