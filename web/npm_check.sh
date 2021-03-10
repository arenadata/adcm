#!/usr/bin/env sh
set -euo pipefail

npm install npm-check
export PATH=$PATH:./node_modules/.bin/
npm config set registry https://rt.adsw.io/artifactory/api/npm/arenadata-npm/
npm i --production
npm-check --production --skip-unused
npm audit
