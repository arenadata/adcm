#!/usr/bin/env bash

for d in $(find /adcm/venv -mindepth 1 -maxdepth 1 -type d); do
    cp -r /adcm/python/ansible/* "${d}/lib/python3.10/site-packages/ansible/"
done;
