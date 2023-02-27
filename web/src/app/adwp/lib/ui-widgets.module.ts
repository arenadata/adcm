import { NgModule } from '@angular/core';

import { AdwpDialogModule } from './dialog/dialog.module';
import { AdwpFormElementModule } from './form-element/form-element.module';
import { AdwpHeaderModule } from './header/header.module';
import { AdwpListModule } from './list/list.module';
import { AdwpLoginFormModule } from './login-form/login-form.module';
import { AdwpNotificationModule } from './notification/notification.module';
import { AdwpToolbarModule } from './toolbar/toolbar.module';

@NgModule({
  declarations: [],
  imports: [
    AdwpLoginFormModule,
    AdwpHeaderModule,
    AdwpListModule,
    AdwpToolbarModule,
    AdwpNotificationModule,
    AdwpDialogModule,
    AdwpFormElementModule,
  ],
  exports: [AdwpLoginFormModule, AdwpHeaderModule, AdwpListModule, AdwpDialogModule, AdwpFormElementModule],
})
export class AdwpUiWidgetsModule {
}
