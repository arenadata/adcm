#!/bin/sh

# Set Yarn version
YARN_VERSION=4.5.0

corepack enable && corepack prepare yarn@$YARN_VERSION
#yarn set version $YARN_VERSION
yarn install
yarn build --mode production --outDir /wwwroot
