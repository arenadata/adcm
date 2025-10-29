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


FROM python:3.10-alpine AS python_builder
ENV PATH="/root/.local/bin:$PATH"
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        bash \
        curl \
        git \
        gnupg \
        libc6-compat \
        libffi \
        libstdc++ \
        libxslt \
        musl-dev \
        openldap-dev \
        openssh-client \
        openssh-keygen \
        openssl \
        rsync \
        sshpass && \
    apk cache clean --purge

ENV PYTHONDONTWRITECODE=1
ENV PYTHONBUFFERED=1

ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/poetry-cache
ENV POETRY_VIRTUALENVS_CREATE=0

ENV EXIT_CODE=0
ENV ANSIBLE_GALAXY_RETRIES=3

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
    $POETRY_VENV/bin/pip install --no-cache-dir poetry==$POETRY_VERSION && \
    $POETRY_VENV/bin/poetry --no-cache --directory=/adcm install --no-root --with ansible,run && \
    python -m venv /adcm/venv/2.9 --system-site-packages --upgrade-deps && \
    /adcm/venv/2.9/bin/pip install --no-cache-dir git+https://github.com/arenadata/ansible.git@v2.9.27-p3 && \
    python -m venv /adcm/venv/2.16 --system-site-packages --upgrade-deps && \
    /adcm/venv/2.16/bin/pip install --no-cache-dir ansible-core==2.16.4 && \
    git clone -b 8.6.8_arenadata1 https://github.com/arenadata/community.general.git && \
    cd community.general && /adcm/venv/2.16/bin/ansible-galaxy collection build && \
    /adcm/venv/2.16/bin/ansible-galaxy collection install /community.general/community-general-8.6.8.tar.gz && \
    curl https://raw.githubusercontent.com/ansible-community/ansible-build-data/refs/heads/main/9/ansible-9.13.0.yaml -o /adcm/ansible-9.13.0.yaml && \
    for retry in $(seq 1 $ANSIBLE_GALAXY_RETRIES); do \
      /adcm/venv/2.16/bin/ansible-galaxy install -r /adcm/ansible-9.13.0.yaml && EXIT_CODE=0 || EXIT_CODE=$?; \
      if [ "$EXIT_CODE" -eq 0 ]; then \
        break; \
      else \
        echo "Attempt $retry failed with code $EXIT_CODE, retrying in 10s..."; \
        sleep 10; \
      fi; \
    done; \
    if [ "$EXIT_CODE" -ne 0 ]; then \
      echo "All $ANSIBLE_GALAXY_RETRIES attempts to install Ansible collections failed (exit code $EXIT_CODE)"; \
      exit $EXIT_CODE; \
    fi && \
    /adcm/venv/2.9/bin/python -m pip uninstall -y pip && \
    /adcm/venv/2.16/bin/python -m pip uninstall -y pip


FROM python:3.10-alpine
ENV PATH="/root/.local/bin:$PATH"
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

RUN python -m pip install -U setuptools

RUN ln -s /usr/local/bin/python3 /usr/bin/python3 && \
    ln -s /usr/bin/python3 /usr/bin/python

COPY os/etc /etc
COPY os/etc/crontabs/root /var/spool/cron/crontabs/root
COPY --from=go_builder /code/bin/runstatus /adcm/go/bin/runstatus
COPY --from=ui_builder /wwwroot /adcm/wwwroot
COPY conf /adcm/conf
COPY python/ansible/plugins /usr/share/ansible/plugins
COPY python /adcm/python
COPY --from=python_builder /adcm/venv /adcm/venv
COPY --from=python_builder /usr/local/bin /usr/local/bin
COPY --from=python_builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=python_builder /root/.ansible/collections /root/.ansible/collections

RUN python -m pip uninstall -y pip && \
    rm -rf /root/.cache/pip
RUN mkdir -p /adcm/data/log

RUN python /adcm/python/manage.py collectstatic --noinput

ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
EXPOSE 8000
CMD ["/etc/startup.sh"]
