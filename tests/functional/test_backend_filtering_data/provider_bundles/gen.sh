#!/bin/bash

# shellcheck disable=SC2086
cd "$(dirname \"${0}\")" || exit 1
TMPL="
---
- type: provider
  name: provider%s
  version: 1

- type: host
  name: host%s
  version: 1
"

for i in $(seq 1 59); do
    mkdir -p "${i}"
    # shellcheck disable=SC2059
    printf "${TMPL}" "${i}" > "${i}/config.yaml"
done
