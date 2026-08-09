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
from django.apps import apps
from django.db import connection
try:
    app_config = apps.get_app_config('app')
    with connection.cursor() as cursor:
        existing_tables = connection.introspection.table_names(cursor)
        for model in app_config.get_models():
            db_table = model._meta.db_table
            if db_table not in existing_tables:
                continue
            existing_cols = [col.name for col in connection.introspection.get_table_description(cursor, db_table)]
            for field in model._meta.concrete_fields:
                col_name = field.column
                if col_name not in existing_cols:
                    internal_type = field.get_internal_type()
                    if internal_type in ['BooleanField', 'NullBooleanField']:
                        sql_type = 'bool NOT NULL DEFAULT 0'
                    elif internal_type in ['IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField', 'ForeignKey', 'OneToOneField']:
                        sql_type = 'integer'
                    elif internal_type in ['FloatField', 'DecimalField']:
                        sql_type = 'real'
                    else:
                        sql_type = 'text'
                    alter_sql = f'ALTER TABLE \"{db_table}\" ADD COLUMN \"{col_name}\" {sql_type};'
                    try:
                        cursor.execute(alter_sql)
                        print(f'Auto-migrated {db_table}: added column {col_name}')
                    except Exception as err:
                        print(f'Warning migrating {db_table}.{col_name}: {err}')
except Exception as e:
    print('Schema check warning:', e)
"
uv run manage.py loaddata units superuser_poshak
uv run uwsgi --ini uwsgi.ini --http-socket :$PORT
