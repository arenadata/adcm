#!/usr/bin/env bash

set -e

pip install -r ./requirements.txt
pip install pytest-django
pytest python
