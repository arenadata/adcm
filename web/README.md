# ADCM Web Client

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 1.5.5.

## Storybook

**Before starting:**
To run Storybook, you need to have been installed Docker (https://www.docker.com/).

**Starting:**

1. Make sure that you have been connected to ADCM VPN
2. Move to ADCM web root directory (usually <some_path>/adcm/web)
3. Run the following command for your OS:

**Linux:**
`docker run -it --rm -v ${pwd}:/web -p 6006:6006 node:14-alpine ./web/storybook.sh`

**Mac OS:**
`docker run -it --rm -v $(pwd):/web -p 6006:6006 node:14-alpine ./web/storybook.sh`

4. Installing dependencies and launching the Storybook will take a couple of minutes
5. Navigate to http://localhost:6006/

**Tip:** The first starting may take about 15 minutes.

## Storybook (development)

1. Run `npm run storybook` for start the Storybook.
2. Navigate to http://localhost:6006/.

## Development server

1. Run `ng serve` for a dev server.
2. Navigate to http://localhost:4200/.

**Tip:** The app will automatically reload if you change any of the source files.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory. Use the `-prod` flag for a production build.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via [Protractor](http://www.protractortest.org/).

## i18n internationalization
Static translations are located in the folder ```web/src/assets/i18n/static/[lang].json``` 
(```[lang]``` is the lang that you're using, for english it could be "en")

Example: 
```json
  {
    "display_name": "Name",
    "version": "Version",
    "license_path": "License text",
    "license": "License status"
  }
```

You can either use the TranslateService, the TranslatePipe or the TranslateDirective to get your translation values:
With the service, it looks like this:
####service:

```typescript
  //async
  translate.get('display_name').subscribe((res: string) => {
    console.log(res);
    //=> 'Name'
  });

  //sync
  const res = translate.instant('display_name');
  console.log(res);
  //=> 'Name'

```

####pipe:

```angular2html
  <div>{{ 'display_name' | translate }}</div>
```

####directive:
```angular2html
  <div translate>display_name</div>
```

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI README](https://github.com/angular/angular-cli/blob/master/README.md).
