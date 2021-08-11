#!/usr/bin/env sh
set -euo pipefail

yarn add npm-check
export PATH=$PATH:./node_modules/.bin/
yarn config set registry https://rt.adsw.io/artifactory/api/npm/arenadata-npm/
yarn install --production
npm-check --production --skip-unused
yarn audit
