#!/usr/bin/env bash

set -eu



_find_venvs(){
    # List all venvs by its names from /adcm/venv dir
    find "/adcm/venv/" -type d -maxdepth 1 -mindepth 1 -exec basename {} \;
}

activate(){
    # Just activate venv by its dir name
    source "/adcm/venv/${1}/bin/activate"
}

run(){
    # Run a command in venv
    activate "${1}"
    shift
    $@
}

reqs(){
    # Install packages from requirements file in venv
    activate "${1}"
    shift
    pip install --no-cache -r "${1}"
}

reqs_and_run(){
    venv_name="${1}"
    shift
    req_file="${1}"
    shift
    reqs "${venv_name}" "${req_file}"
    run "${venv_name}" $@
}

any(){
    # Do something for every venv
    for v in $(_find_venvs); do
        run "${v}" $@
    done
}

$@
