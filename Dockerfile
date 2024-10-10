FROM golang:1.23 AS go_builder
COPY ./go /code
WORKDIR /code
RUN sh -c "make"


FROM node:20.9.0-alpine AS ui_builder
ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
COPY ./adcm-web/app /code
WORKDIR /code
RUN . build.sh


FROM python:3.10-alpine
ENV PATH="/root/.local/bin:$PATH"
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        bash \
        git \
        gnupg \
        libc6-compat \
        libffi \
        libstdc++ \
        libxslt \
        musl-dev \
        nginx \
        openldap-dev \
        openssh-client \
        openssh-keygen \
        openssl \
        rsync \
        runit \
        sshpass && \
    apk cache clean --purge

ENV PYTHONDONTWRITECODE=1
ENV PYTHONBUFFERED=1

ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/poetry-cache
ENV POETRY_VIRTUALENVS_CREATE=0

COPY poetry.lock pyproject.toml /adcm/

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        linux-headers \
        libffi-dev && \
    # remove python links (3.12) from /usr/bin and link python to local one (3.10)
    rm /usr/bin/python /usr/bin/python3 && \
    ln -s /usr/local/bin/python3 /usr/bin/python3 && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    python -m venv $POETRY_VENV && \
    $POETRY_VENV/bin/pip install --no-cache-dir -U pip setuptools && \
    $POETRY_VENV/bin/pip install --no-cache-dir poetry==$POETRY_VERSION && \
    $POETRY_VENV/bin/poetry --no-cache --directory=/adcm install --no-root && \
    python -m venv /adcm/venv/2.9 --system-site-packages && \
    /adcm/venv/2.9/bin/pip install --no-cache-dir git+https://github.com/arenadata/ansible.git@v2.9.27-p1 && \
    $POETRY_VENV/bin/poetry cache clear pypi --all && \
    apk del .build-deps && \
    apk cache clean --purge && \
    rm -rf $POETRY_HOME && \
    rm -rf $POETRY_VENV && \
    rm -rf $POETRY_CACHE_DIR

RUN rm /adcm/poetry.lock /adcm/pyproject.toml

COPY os/etc /etc
COPY os/etc/crontabs/root /var/spool/cron/crontabs/root
COPY --from=go_builder /code/bin/runstatus /adcm/go/bin/runstatus
COPY --from=ui_builder /wwwroot /adcm/wwwroot
COPY conf /adcm/conf
COPY python/ansible/plugins /usr/share/ansible/plugins
COPY python /adcm/python

RUN mkdir -p /adcm/data/log

RUN python /adcm/python/manage.py collectstatic --noinput

ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
EXPOSE 8000
CMD ["/etc/startup.sh"]
