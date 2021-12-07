import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacGroupFormComponent } from './rbac-group-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { RbacUsersAsOptionsModule } from '../user-form/options/rbac-users-as-options.module';
import { AdwpFormElementModule } from '@adwp-ui/widgets';


@NgModule({
  declarations: [
    RbacGroupFormComponent,
  ],
  exports: [
    RbacGroupFormComponent,
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    RbacUsersAsOptionsModule,
  ],
})
export class RbacGroupFormModule {
}
