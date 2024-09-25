FROM python:3.10-alpine
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml poetry.lock /adcm/

RUN apk update && \
    apk upgrade && \
    apk add --virtual .build-deps \
        build-base \
        linux-headers && \
    apk add \
        bash \
        curl \
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
        sshpass \
        libffi-dev && \
    curl -sSL https://install.python-poetry.org | POETRY_HOME=/tmp/poetry python - && \
    /tmp/poetry/bin/poetry config virtualenvs.create false && \
    /tmp/poetry/bin/poetry --directory=/adcm install --no-root && \
    python -m venv /adcm/venv/2.9 --system-site-packages && \
    . /adcm/venv/2.9/bin/activate && \
    pip install git+https://github.com/arenadata/ansible.git@v2.9.27-p1 && \
    deactivate && \
    apk del .build-deps && \
    /tmp/poetry/bin/poetry cache clear pypi --all && \
    rm -rf /root/.cache && \
    rm -rf /var/cache/apk/* && \
    rm -rf /tmp/poetry

COPY . /adcm
RUN mkdir -p /adcm/data/log && \
    mkdir -p /usr/share/ansible/plugins/modules && \
    cp -r /adcm/os/* / && \
    cp /adcm/os/etc/crontabs/root /var/spool/cron/crontabs/root && \
    cp -r /adcm/python/ansible/* /usr/local/lib/python3.10/site-packages/ansible/ && \
    cp -r /adcm/python/ansible/* /adcm/venv/2.9/lib/python3.10/site-packages/ansible/ && \
    python /adcm/python/manage.py collectstatic --noinput && \
    cp -r /adcm/wwwroot/static/rest_framework/css/* /adcm/wwwroot/static/rest_framework/docs/css/
ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
EXPOSE 8000
CMD ["/etc/startup.sh"]
