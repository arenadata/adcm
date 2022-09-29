FROM python:3.10-slim
RUN apt update && \
    apt upgrade -y --no-install-recommends &&  \
    apt install -y --no-install-recommends \
        git \
        gcc \
        libldap2-dev \
        libsasl2-dev \
        runit \
        cron \
        nginx \
        openssh-client
COPY requirements*.txt /adcm/
RUN pip install --upgrade pip &&  \
    pip install --no-cache-dir -r /adcm/requirements.txt && \
    pip install --no-cache-dir -r /adcm/requirements-venv-default.txt && \
    virtualenv --system-site-packages /adcm/venv/2.9 && \
    . /adcm/venv/2.9/bin/activate && \
    pip install --no-cache-dir -r /adcm/requirements-venv-2.9.txt && \
    deactivate && \
    virtualenv --system-site-packages /adcm/venv/default &&  \
    . /adcm/venv/default/bin/activate && \
    pip install --no-cache-dir -r /adcm/requirements-venv-default.txt && \
    deactivate
COPY . /adcm
RUN cp -r /adcm/os/* / && \
    cp /adcm/os/etc/crontabs/root /var/spool/cron/crontabs/root && \
    cp -r /adcm/python/ansible/ /adcm/venv/default/lib/python3.10/site-packages/ansible/ && \
    cp -r /adcm/python/ansible/ /adcm/venv/2.9/lib/python3.10/site-packages/ansible/ && \
    mkdir -p /adcm/data/log && \
    python /adcm/python/manage.py collectstatic --noinput && \
    cp -r /adcm/wwwroot/static/rest_framework/css/* /adcm/wwwroot/static/rest_framework/docs/css/
EXPOSE 8000
CMD ["/etc/startup.sh"]
