import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRoleFormComponent } from './rbac-role-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '@adwp-ui/widgets';
import { AdcmInputRbacPermissionModule } from '../../../shared/form-elements/adcm-input-rbac-permission/adcm-input-rbac-permission.module';
import { RbacPermissionFormModule } from '../permission-form/rbac-permission-form.module';
import { RbacRolesAsOptionsModule } from './options/rbac-roles-as-options.module';


@NgModule({
  declarations: [
    RbacRoleFormComponent
  ],
  exports: [
    RbacRoleFormComponent
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    AdcmInputRbacPermissionModule,
    RbacPermissionFormModule,
    RbacRolesAsOptionsModule
  ],
})
export class RbacRoleFormModule {
}
