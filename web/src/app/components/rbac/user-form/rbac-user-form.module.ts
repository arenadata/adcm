import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacUserFormComponent } from './rbac-user-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { RbacGroupFormModule } from '../group-form/rbac-group-form.module';
import { RbacGroupsAsOptionsModule } from '../group-form/options/rbac-groups-as-options.module';
import { AdwpFormElementModule } from '@adwp-ui/widgets';
import { FalseAsEmptyArrayModule } from '../../../shared/pipes/false-as-empty-array/false-as-empty-array.module';


@NgModule({
  declarations: [
    RbacUserFormComponent,
  ],
  exports: [
    RbacUserFormComponent,
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    RbacGroupFormModule,
    RbacGroupsAsOptionsModule,
    FalseAsEmptyArrayModule
  ],
})
export class RbacUserFormModule {
}
