FROM ghcr.io/astral-sh/uv:alpine

RUN apk add --update gcc linux-headers musl-dev openldap-dev python3-dev bash make

# set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create the directory for the code and jump into it
RUN mkdir /var/www && mkdir /var/www/cobbled
WORKDIR /var/www/cobbled

# Copy across the project details, build the virtual environment and populate the DB.
COPY . .
RUN uv run sync  # --extra develop; If you want to install the debug mode requirements.

# uWSGI wants to be run from inside the project directory, so we have to copy the env files there.
COPY .env* cobbled/.
WORKDIR cobbled

# Ensure all files are owned by UID 1000 for Hugging Face Spaces compatibility
RUN chown -R 1000:1000 /var/www && chmod -R 775 /var/www

ENTRYPOINT ["bash", "docker-entrypoint.sh"]

