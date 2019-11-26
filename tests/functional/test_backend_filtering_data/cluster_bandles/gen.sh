#!/bin/bash

# shellcheck disable=SC2086
cur=$(dirname "${0}")
cd "$cur" || exit 1
TMPL="
---
- type: cluster
  name: %s
  version: ver%s
"

for i in $(seq 1 59); do
    mkdir -p "${i}"
    # shellcheck disable=SC2059
    printf "${TMPL}" "${i}" "${i}" > "${i}/config.yaml"
done
