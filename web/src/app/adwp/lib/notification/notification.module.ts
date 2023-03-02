import { NgModule, Optional, SkipSelf } from '@angular/core';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { NotificationService } from '../services/notification.service';

@NgModule({
  imports: [
    MatSnackBarModule,
  ],
  providers: [
    NotificationService,
  ]
})
export class AdwpNotificationModule {

  constructor(@Optional() @SkipSelf() parentModule?: AdwpNotificationModule) {
    if (parentModule) {
      throw new Error('AdwpNotificationModule is already loaded. Import it in the AppModule only');
    }
  }

}
