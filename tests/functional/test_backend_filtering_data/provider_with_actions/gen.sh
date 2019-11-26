#!/bin/bash

# shellcheck disable=SC2086
cur=$(dirname "${0}")
cd "$cur" || exit 1
TMPL="
---
- type: provider
  name: provider_with_actions
  version: 1
  actions: &actions

"

ACTION_TMPLS="
    ok%s:
        type: job
        script: ok.yaml
        script_type: ansible
        states:
            available: any

    fail%s:
        type: job
        script: fail.yaml
        script_type: ansible
        states:
            available: any
"

HOST_TMPL="

- type: host
  name: host_with_actions
  version: 1
  actions: *actions

"

echo "${TMPL}" > "./config.yaml"

for i in $(seq 0 59); do
    # shellcheck disable=SC2059
    printf "${ACTION_TMPLS}" "${i}" "${i}" >> "./config.yaml"
done

echo "${HOST_TMPL}" >> "./config.yaml"
