#!/usr/bin/env sh
set -eu

yarn config set registry https://rt.adsw.io/artifactory/api/npm/arenadata-npm/
export CHROME_BIN=/usr/bin/google-chrome
yarn install
yarn test -- --watch=false
