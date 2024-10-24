FROM node:20.9.0-alpine

WORKDIR /app

RUN yarn set version berry
RUN yarn plugin import workspace-tools

COPY ./app/package.json ./app/yarn.lock ./
RUN yarn install && yarn cache clean
#RUN yarn workspaces focus --production

COPY ./app .

RUN yarn build --mode testing

CMD yarn preview --host
