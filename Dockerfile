FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libldap2-dev \
    libsasl2-dev \
    libxml2-dev \
    libxslt-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    pkg-config \
    bash \
    make \
    && rm -rf /var/lib/apt/lists/*

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

