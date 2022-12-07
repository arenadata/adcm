#!/usr/bin/env bash

if [[ "${1}" != "none" ]]; then
    venv="/adcm/venv/${1}/bin/activate"
    . "${venv}"
fi

shift

"$@"
