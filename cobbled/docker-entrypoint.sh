if [ -n "$SPACE_ID" ]; then
    PORT=${PORT:-7860}
else
    PORT=${PORT:-8000}
fi

uv run manage.py collectstatic --noinput
uv run manage.py makemigrations
uv run manage.py migrate --noinput
uv run uwsgi --ini uwsgi.ini --http-socket :$PORT
