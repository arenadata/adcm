import { ModuleWithProviders, NgModule, Optional, SkipSelf } from '@angular/core';

import { AuthService } from '../services/auth.service';
import { AuthConfig } from './auth-config';
import { AuthConfigService } from './auth-config.service';

@NgModule({
  providers: [
    AuthService,
  ],
})
export class AdwpAuthModule {

  constructor(@Optional() @SkipSelf() parentModule?: AdwpAuthModule) {
    if (parentModule) {
      throw new Error('AdwpAuthModule is already loaded. Import it in the AppModule only');
    }
  }

  public static forRoot(config: AuthConfig): ModuleWithProviders<AdwpAuthModule> {
    return {
      ngModule: AdwpAuthModule,
      providers: [
        {
          provide: AuthConfigService,
          useValue: config,
        }
      ]
    };
  }

}
