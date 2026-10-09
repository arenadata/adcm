# The ansible environments are built and published by the ansible-environments repo; this
# build layers ADCM's own dependencies onto them rather than assembling its own venvs.
ARG ANSIBLE_216_IMAGE=hub.adsw.io/ansible/ansible:2.16.4-python3.10-musl-develop
ARG ANSIBLE_221_IMAGE=hub.adsw.io/ansible/ansible:2.21.4-python3.12-musl-develop

FROM golang:1.26 AS go_builder
COPY ./go /code
WORKDIR /code
RUN sh -c "make"


FROM node:20.9.0-alpine AS ui_builder
ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
COPY ./adcm-web/app /code
WORKDIR /code
RUN . build.sh


FROM alpine:3.24 AS python_builder

RUN apk add --no-cache --virtual .build-deps \
    build-base \
    linux-headers \
    openldap-dev

ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_PREFERENCE=only-managed
ENV UV_PYTHON_INSTALL_DIR=/python

WORKDIR /adcm

# Prepare venv Python 3.12 for ADCM
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --python 3.12.14 --group run --locked

RUN /python/cpython-3.12-linux-x86_64-musl/bin/python3.12 -m pip uninstall -y --break-system-packages pip

# Only ADCM's own dependencies are layered onto each tree. They are needed because the
# arenadata.adcm plugins run under these interpreters and import adcm/cm, which pulls Django.
FROM ${ANSIBLE_216_IMAGE} AS env_216

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,id=uv-adcm-2.16,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    UV_PYTHON_DOWNLOADS=0 \
    uv export --locked --no-emit-project --only-group adcm-plugins  \
        --no-emit-package ansible-core --no-emit-package resolvelib \
        --format requirements.txt --python 3.10 -o /tmp/adcm-layer.txt && \
    UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=0 \
    uv pip install --python /venv/2.16/bin/python -r /tmp/adcm-layer.txt && \
    /venv/2.16/bin/python -c "\
import ansible, django; \
from importlib.metadata import version; \
print('ansible', ansible.__version__, '| django', django.__version__)"


FROM ${ANSIBLE_221_IMAGE} AS env_221

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,id=uv-adcm-2.21,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    UV_PYTHON_DOWNLOADS=0 \
    uv export --locked --no-emit-project --only-group adcm-plugins \
        --no-emit-package ansible-core --no-emit-package resolvelib \
        --format requirements.txt --python 3.12 -o /tmp/adcm-layer.txt && \
    UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=0 \
    uv pip install --python /venv/2.21/bin/python -r /tmp/adcm-layer.txt && \
    /venv/2.21/bin/python -c "\
import ansible, django; \
from importlib.metadata import version; \
print('ansible', ansible.__version__, '| django', django.__version__)"


FROM alpine:3.24

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

# Non-root runtime user. Writable state is relocated off root-owned paths (/run, /root) onto
# /adcm/data and the user's home. The uid/gid are build args so they are declared and stable: existing installs
# upgrading from a root-based image must `chown -R ${ADCM_UID}:${ADCM_GID}` their /adcm/data volume once.
ARG ADCM_UID=10001
ARG ADCM_GID=10001
RUN addgroup -g "${ADCM_GID}" adcm && \
    adduser -D -u "${ADCM_UID}" -G adcm -h /home/adcm -s /bin/sh adcm

COPY os/etc /etc
# Point each runit service's supervise/ dir at the ephemeral runtime dir: the
# service run-scripts stay root-owned, and only /adcm/run is writable. The
# target is a fixed path with no uid in it, so the image also works when the
# platform assigns an arbitrary runtime uid (e.g. OpenShift).
RUN for svc in /etc/sv/*/; do \
        ln -s "/adcm/run/runit/$(basename "${svc}")" "${svc}supervise"; \
    done
COPY --from=go_builder --chown=adcm:adcm /code/bin/runstatus /adcm/go/bin/runstatus
COPY --from=ui_builder --chown=adcm:adcm /wwwroot /adcm/wwwroot
COPY --from=python_builder --chown=adcm:adcm /python /python
COPY --from=python_builder --chown=adcm:adcm /adcm/.venv /adcm/.venv
COPY --from=env_216 --chown=adcm:adcm /venv/2.16 /venv/2.16
COPY --from=env_221 --chown=adcm:adcm /venv/2.21 /venv/2.21
COPY --chown=adcm:adcm conf /adcm/conf
COPY --chown=adcm:adcm python/ansible_collections/arenadata/adcm/plugins /usr/share/ansible/plugins
COPY --chown=adcm:adcm python/ansible_collections/arenadata/adcm /venv/2.16/collections/ansible_collections/arenadata/adcm
COPY --chown=adcm:adcm python/ansible_collections/arenadata/adcm /venv/2.21/collections/ansible_collections/arenadata/adcm
COPY --chown=adcm:adcm python /adcm/python

# For bundle content that hardcodes an absolute interpreter path; ADCM itself always goes
# through PATH. No python3.12 link: ansible probes it first and 2.16 jobs would get 2.21.
RUN ln -s /venv/2.16/bin/python3.10 /usr/bin/python3.10 && \
    ln -s python3.10 /usr/bin/python3 && \
    ln -s python3 /usr/bin/python && \
    ln -s /tmp/.ansible /home/adcm/.ansible  && \
    ln -s /adcm/python/application/scripts/manage_secrets.py /adcm/python/manage_secrets.py && \
    chown -h adcm:adcm /adcm/python/manage_secrets.py

# Every name ansible's interpreter discovery probes has to land inside a venv, or a distro
# python arriving as someone's dependency would silently take over every task.
RUN for name in python3.13 python3.12 python3.11 python3.10 python3 python; do \
        found=$(command -v "${name}" || true); \
        [ -z "${found}" ] || \
        [ "$(readlink -f "${found}")" = "/venv/2.16/bin/python3.10" ] || \
            { echo "interpreter discovery would pick ${name} -> ${found}"; exit 1; }; \
    done && \
    command -v python3.10 python3 python && \
    /adcm/.venv/bin/python -m compileall -q -j 0 /adcm/python && \
    /venv/2.16/bin/python -m compileall -q -j 0 /venv/2.16/collections/ansible_collections/arenadata/adcm && \
    /venv/2.21/bin/python -m compileall -q -j 0 /venv/2.21/collections/ansible_collections/arenadata/adcm && \
    find /adcm/python -type d -name "__pycache__" -exec chown -R adcm:adcm {} + && \
    find /venv/2.16/collections/ansible_collections/arenadata/adcm -type d -name "__pycache__" -exec chown -R adcm:adcm {} + && \
    find /venv/2.21/collections/ansible_collections/arenadata/adcm -type d -name "__pycache__" -exec chown -R adcm:adcm {} +

# Hand only the runtime-writable paths to the non-root user; the enabled ssl vhost
# is written to /adcm/data (see make_nginx_default_config).
#   /adcm      - code, wwwroot/static, and /adcm/data
#   /adcm/run  - ephemeral runtime state (uwsgi pidfile + wsgi socket, runit
#                supervise dirs); mode 0700 (the supervise control FIFOs allow
#                signalling services); tmpfs it under a read-only rootfs
RUN mkdir -p /adcm/data/log /adcm/run && \
    chmod 700 /adcm/run && \
    chown -R adcm:adcm /adcm/run /adcm/data

RUN DJANGO_SETTINGS_MODULE=adcm.settings_setups.build /adcm/.venv/bin/python /adcm/python/manage.py collectstatic --noinput && \
    chown -R adcm:adcm /adcm/wwwroot/static

ENV PYTHONPATH=/adcm/python
ENV HOME=/home/adcm
# Everything ansible writes under ~/.ansible by default is rebased onto /tmp,
# so HOME needs no writable mount under a read-only rootfs and the ephemeral
# files stay off the data volume.The symlink covers `remote_tmp`
# for connection=local plays: it always expands literally to ~/.ansible/tmp and
# cannot be redirected globally without also breaking remote (ssh) targets.
ENV ANSIBLE_HOME=/tmp/.ansible
ARG ADCM_VERSION
ENV ADCM_VERSION=$ADCM_VERSION
EXPOSE 8000
USER ${ADCM_UID}:${ADCM_GID}
CMD ["/etc/startup.sh"]
