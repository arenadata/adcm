#!/bin/sh
cd /web
npm config set registry https://rt.adsw.io/artifactory/api/npm/arenadata-npm/
yarn install
yarn run storybook
