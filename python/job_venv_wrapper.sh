#!/usr/bin/env bash

# Source virtualenv if it is required
if [[ "${1}" != "none" ]]; then
    venv="/adcm/venv/${1}/bin/activate"
    # shellcheck disable=SC1090
    . "${venv}"
fi

shift

# run command
"$@"
