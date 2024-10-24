# Arenadata Cluster Manager Frontend

This is documentation for ADCM Frontend project part

## Development

### Requirements
1. Node > 20.9.x (recommend use [NVM](https://github.com/nvm-sh/nvm))
2. yarn > v4.5.x   ([yarn v4 install](https://yarnpkg.com/getting-started/install))

### Start local Backend
```
docker pull hub.adsw.io/adcm/adcm:develop
docker run --rm -d -p 8000:8000 hub.adsw.io/adcm/adcm:develop
```

### Start dev version
```
cd ./adcm-web/app
yarn install
yarn start
```

### Build prod version
```
cd ./adcm-web/app
yarn install
yarn build
```

### Run tests
```
cd ./adcm-web/app
yarn install
yarn test
```

### Start Storybook
```
cd ./adcm-web/app
yarn install
yarn storybook
```

### Code
We use eslint and prettier. Make sure that you IDE use configs in this project

We use code styles. Read this [article](https://wiki.adsw.io/books/frontend/page/code-styles-guide)
