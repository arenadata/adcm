import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacGroupFormComponent } from './rbac-group-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { RbacUsersAsOptionsModule } from '../user-form/options/rbac-users-as-options.module';
import { AdwpFormElementModule } from '@app/adwp';
import { FalseAsEmptyArrayModule } from '../../../shared/pipes/false-as-empty-array/false-as-empty-array.module';


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
    FalseAsEmptyArrayModule,
  ],
})
export class RbacGroupFormModule {
}
