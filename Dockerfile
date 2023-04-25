FROM python:3.10-alpine
RUN apk update && \
    apk upgrade && \
    apk add --virtual .build-deps \
        build-base \
        linux-headers && \
    apk add \
        bash \
        curl \
        git \
        libc6-compat \
        libffi \
        libstdc++ \
        libxslt \
        logrotate \
        musl-dev \
        nginx \
        openldap-dev \
        openssh-client \
        openssh-keygen \
        openssl \
        rsync \
        runit \
        sshpass && \
    curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml /adcm/
RUN python -m venv /adcm/venv/2.9 && \
    poetry config virtualenvs.create false && \
    poetry -C /adcm install --no-root && \
    cp -r /usr/local/lib/python3.10/site-packages /adcm/venv/2.9/lib/python3.10 && \
    . /adcm/venv/2.9/bin/activate && \
    pip install git+https://github.com/arenadata/ansible.git@v2.9.27-p1 && \
    deactivate
RUN apk del .build-deps
COPY . /adcm
RUN mkdir -p /adcm/data/log && \
    mkdir -p /usr/share/ansible/plugins/modules && \
    cp -r /adcm/os/* / && \
    cp /adcm/os/etc/crontabs/root /var/spool/cron/crontabs/root && \
    cp -r /adcm/python/ansible/* /usr/local/lib/python3.10/site-packages/ansible/ && \
    cp -r /adcm/python/ansible/* /adcm/venv/2.9/lib/python3.10/site-packages/ansible/ && \
    python /adcm/python/manage.py collectstatic --noinput && \
    cp -r /adcm/wwwroot/static/rest_framework/css/* /adcm/wwwroot/static/rest_framework/docs/css/
EXPOSE 8000
CMD ["/etc/startup.sh"]
