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
import { EffectsModule } from '@ngrx/effects';
import { StoreModule } from '@ngrx/store';
import { StoreDevtoolsModule } from '@ngrx/store-devtools';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { HttpClient } from '@angular/common/http';
import { AdwpPortalHostModule, AdwpUiWidgetsModule } from '@app/adwp';

import { CoreModule } from '@app/core/core.module';
import { ConfigService } from '@app/core/services';
import { reducers, StoreEffects } from '@app/core/store';
import { environment } from '@env/environment';
import { AppComponent } from './app.component';
import { EntryModule } from './entry/entry.module';
import { MainModule } from './main/main.module';
import { SharedModule } from './shared/shared.module';
import { LogComponent } from './ws-logs/log.component';
import { appInitializer, translateLoader } from '@app/shared/translate/intializer';
import { AppRoutingModule } from '@app/app-routing.module';
import { ListService } from '@app/shared/components/list/list.service';
import { LIST_SERVICE_PROVIDER } from '@app/shared/components/list/list-service-token';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { AddService } from '@app/shared/add-component/add.service';
import { SnackBarComponent } from './components/snack-bar/snack-bar.component';
import { RouterHistoryService } from '@app/core/services/router-history.service';

@NgModule({
  declarations: [
    AppComponent,
    LogComponent,
    SnackBarComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    CoreModule,
    SharedModule,
    EntryModule,
    MainModule,
    AppRoutingModule,
    StoreModule.forRoot(reducers),
    EffectsModule.forRoot(StoreEffects),
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
    AdwpPortalHostModule,
  ],
  bootstrap: [AppComponent],
  providers: [
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
    },
    {
      provide: APP_INITIALIZER,
      useFactory: (routerHistory: RouterHistoryService) => () => routerHistory.reset(),
      deps: [RouterHistoryService],
      multi: true
    },
    {
      provide: LIST_SERVICE_PROVIDER,
      useClass: ListService
    },
    {
      provide: ADD_SERVICE_PROVIDER,
      useClass: AddService
    }
  ],
})
export class AppModule {
}
