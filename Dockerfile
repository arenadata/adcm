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


FROM python:3.10-alpine3.24 AS python_builder

RUN apk add --no-cache --virtual .build-deps \
    build-base \
    linux-headers \
    openldap-dev

ENV UV_PYTHON_INSTALL_DIR=/python

# Install Python 3.12
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv python install 3.12

WORKDIR /adcm

# Prepare venv Python 3.12 for ADCM
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --python 3.12 --group run --locked

# Prepare venv Python 3.10 for Ansible 2.16
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=ansible-2.16-python3.10-dependencies.txt,target=ansible-2.16-python3.10-dependencies.txt \
    uv venv -p 3.10 /venv/2.16 && \
    source /venv/2.16/bin/activate && \
    uv pip install -p 3.10 -r ansible-2.16-python3.10-dependencies.txt


FROM python:3.10-alpine3.24

RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
    bash \
    gnupg \
    nginx \
    openldap \
    openssh-client \
    openssh-keygen \
    openssl \
    rsync \
    runit \
    sshpass && \
    apk cache clean --purge

RUN python3.10 -m pip install -U setuptools && \
    python3.10 -m pip uninstall -y pip && \
    rm -rf /root/.cache/pip

COPY os/etc /etc
COPY os/etc/crontabs/root /var/spool/cron/crontabs/root
COPY --from=go_builder /code/bin/runstatus /adcm/go/bin/runstatus
COPY --from=ui_builder /wwwroot /adcm/wwwroot
COPY --from=python_builder /python /python
COPY --from=python_builder /adcm/.venv /adcm/.venv
COPY --from=python_builder /venv/2.16 /venv/2.16
COPY --from=arenadata/ansible:2.16.4-python3.10 /venv/2.16 /venv/2.16
COPY --from=arenadata/ansible:2.16.4-python3.10 /root/.ansible/collections /root/.ansible/collections
COPY conf /adcm/conf
COPY python/ansible_collections/arenadata/adcm/plugins /usr/share/ansible/plugins
COPY python/ansible_collections/arenadata/adcm /root/.ansible/collections/ansible_collections/arenadata/adcm
COPY python /adcm/python

RUN ln -s -f /usr/local/bin/python3 /usr/bin/python3 && \
    ln -s -f /usr/bin/python3 /usr/bin/python

RUN ln -s /adcm/python/application/scripts/manage_secrets.py /adcm/python/manage_secrets.py

RUN mkdir -p /adcm/data/log

RUN DJANGO_SETTINGS_MODULE=adcm.settings_setups.build /adcm/.venv/bin/python /adcm/python/manage.py collectstatic --noinput

ENV PYTHONPATH=/adcm/python

ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
EXPOSE 8000
CMD ["/etc/startup.sh"]
