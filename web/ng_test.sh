#!/usr/bin/env sh
set -eu

npm config set registry https://rt.adsw.io/artifactory/api/npm/arenadata-npm/
export CHROME_BIN=/usr/bin/google-chrome
npm install
ng test --watch=false
