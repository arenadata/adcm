#!/usr/bin/env sh
set -eu

export CHROME_BIN=/usr/bin/google-chrome
npm install
ng test --watch=false
