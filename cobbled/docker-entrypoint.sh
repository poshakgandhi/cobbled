uv run manage.py collectstatic --noinput
uv run manage.py makemigrations
uv run manage.py migrate --noinput
uv run uwsgi --ini uwsgi.ini
