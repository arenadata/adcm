import { ModuleWithProviders, NgModule, Optional, SkipSelf } from '@angular/core';
import { ApiService } from '../services/api.service';
import { ApiConfigService } from './api-config.service';
import { ApiConfig } from './api-config';

@NgModule({
  providers: [
    ApiService,
  ],
})
export class AdwpApiModule {

  constructor(@Optional() @SkipSelf() parentModule?: AdwpApiModule) {
    if (parentModule) {
      throw new Error('AdwpApiModule is already loaded. Import it in the AppModule only');
    }
  }

  public static forRoot(config: ApiConfig): ModuleWithProviders<AdwpApiModule> {
    return {
      ngModule: AdwpApiModule,
      providers: [
        {
          provide: ApiConfigService,
          useValue: config,
        }
      ]
    };
  }

}
