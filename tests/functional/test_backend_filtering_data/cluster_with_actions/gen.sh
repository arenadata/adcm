#!/bin/bash

# shellcheck disable=SC2086
cur=$(dirname "${0}")
cd "$cur" || exit 1
TMPL="
---
- type: cluster
  name: cluster_with_actions
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

SERVICE_TMPL="

- type: service
  name: service_with_actions
  version: 1
  actions: *actions

"

echo "${TMPL}" > "./config.yaml"

for i in $(seq 0 59); do
    # shellcheck disable=SC2059
    printf "${ACTION_TMPLS}" "${i}" "${i}" >> "./config.yaml"
done

echo "${SERVICE_TMPL}" >> "./config.yaml"
