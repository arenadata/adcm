import { ModuleWithProviders, NgModule } from '@angular/core';

import { SocketConfigService } from '../services/socket-config.service';
import { SocketService } from '../services/socket.service';
import { SocketConfig } from './socket-config';

@NgModule({
  providers: [
    SocketService,
  ]
})
export class AdwpSocketModule {

  public static forRoot(config: SocketConfig): ModuleWithProviders<AdwpSocketModule> {
    return {
      ngModule: AdwpSocketModule,
      providers: [
        {
          provide: SocketConfigService,
          useValue: config,
        }
      ]
    };
  }

}
