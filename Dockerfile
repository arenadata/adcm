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
WORKDIR /adcm
RUN python -m venv venv/2.9 && \
    python -m venv venv/default &&  \
    poetry config virtualenvs.create false && \
    poetry install --no-root && \
    cp -r /usr/local/lib/python3.10/site-packages venv/2.9/lib/python3.10 && \
    cp -r /usr/local/lib/python3.10/site-packages venv/default/lib/python3.10 && \
    . venv/2.9/bin/activate && \
    pip install git+https://github.com/arenadata/ansible.git@v2.9.27-p1 && \
    deactivate
RUN apk del .build-deps
COPY . /adcm
RUN mkdir -p data/log && \
    mkdir -p /usr/share/ansible/plugins/modules && \
    cp -r os/* / && \
    cp os/etc/crontabs/root /var/spool/cron/crontabs/root && \
    cp -r python/ansible/* venv/default/lib/python3.10/site-packages/ansible/ && \
    cp -r /adcm/python/ansible/* venv/2.9/lib/python3.10/site-packages/ansible/ && \
    python python/manage.py collectstatic --noinput && \
    cp -r wwwroot/static/rest_framework/css/* wwwroot/static/rest_framework/docs/css/
EXPOSE 8000
CMD ["/etc/startup.sh"]
