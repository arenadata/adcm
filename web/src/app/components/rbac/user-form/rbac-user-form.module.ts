import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacUserFormComponent } from './rbac-user-form.component';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { ReactiveFormsModule } from '@angular/forms';
import { RbacGroupFormModule } from '../group-form/rbac-group-form.module';
import { RbacGroupsAsOptionsModule } from '../group-form/options/rbac-groups-as-options.module';


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
    RbacGroupsAsOptionsModule
  ],
})
export class RbacUserFormModule {
}
