import { HttpClient } from '@angular/common/http';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { TranslateService } from '@ngx-translate/core';
import { Injector } from '@angular/core';
import { LOCATION_INITIALIZED } from '@angular/common';

export function translateLoader(http: HttpClient) {
  return new TranslateHttpLoader(http, './assets/i18n/static/', '.json');
}

export function appInitializer(translate: TranslateService, injector: Injector) {
  return () => new Promise<any>(
    (resolve: any) => {
      const locationInitialized = injector.get(LOCATION_INITIALIZED, Promise.resolve(null));
      locationInitialized.then(
        () => {
          const langToSet = 'en';
          translate.setDefaultLang('en');
          translate.use(langToSet).subscribe(
            () => { },
            (e) => console.error('Error while changing the currently used language', e),
            () => {
              resolve(null);
            });
        },
        (e) => console.error('Error initializing location', e));
    });
}
