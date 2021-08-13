#!/bin/sh
cd /web
npm config set registry https://rt.adsw.io/artifactory/api/npm/arenadata-npm/
echo n | npm install
npm run storybook
