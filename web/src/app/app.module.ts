// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { APP_INITIALIZER, Injector, NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterModule } from '@angular/router';
import { ConfigService, CoreModule } from '@app/core';
import { reducers, StoreEffects } from '@app/core/store';
import { EffectsModule } from '@ngrx/effects';
import { StoreModule } from '@ngrx/store';
import { StoreDevtoolsModule } from '@ngrx/store-devtools';

import { environment } from '@env/environment';
import { AppComponent } from './app.component';
import { EntryModule } from './entry/entry.module';
import { MainModule } from './main/main.module';
import { SharedModule } from './shared/shared.module';
import { LogComponent } from './ws-logs/log.component';
import { AdwpUiWidgetsModule } from '@adwp-ui/widgets';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { HttpClient } from '@angular/common/http';
import { appInitializer, translateLoader } from '@app/shared/translate/intializer';

//registerLocaleData(localeRu, 'ru');

@NgModule({
  declarations: [
    AppComponent,
    LogComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    CoreModule,
    SharedModule,
    EntryModule,
    MainModule,
    RouterModule.forRoot([], { relativeLinkResolution: 'legacy' }),
    StoreModule.forRoot(reducers),
    EffectsModule.forRoot(StoreEffects),
    // StoreRouterConnectingModule.forRoot(),
    !environment.production ? StoreDevtoolsModule.instrument() : [],
    TranslateModule.forRoot({
      defaultLanguage: 'en',
      loader: {
        provide: TranslateLoader,
        useFactory: translateLoader,
        deps: [HttpClient]
      }
    }),
    AdwpUiWidgetsModule,
  ],
  bootstrap: [AppComponent],
  providers: [
    //{ provide: LOCALE_ID, useValue: 'ru' },
    {
      provide: APP_INITIALIZER,
      useFactory: (appConfig: ConfigService) => () => appConfig.load(),
      deps: [ConfigService],
      multi: true,
    },
    {
      provide: APP_INITIALIZER,
      useFactory: appInitializer,
      deps: [TranslateService, Injector],
      multi: true
    }
    // { provide: RouterStateSerializer, useClass: RouteSerializer },
  ],
})
export class AppModule {}
