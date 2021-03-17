#!/usr/bin/env sh
set -eu

apk add --update --no-cache --virtual .pynacl_deps build-base python3-dev libffi-dev openssl-dev linux-headers libxslt-dev rust cargo
apk add --update --no-cache libffi openssl libxslt libstdc++
apk add --update --no-cache nginx sshpass runit openssh-keygen openssh-client git dcron logrotate curl rsync
pip install --no-cache-dir -r /requirements-base.txt
rm /requirements-base.txt
apk del git
apk del .pynacl_deps
rm /etc/nginx/conf.d/default.conf
