#!/bin/sh

yarn set version berry
yarn install
yarn build --mode production --outDir /wwwroot
