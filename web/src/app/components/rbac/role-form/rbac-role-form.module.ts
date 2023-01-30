import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRoleFormComponent } from './rbac-role-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '@app/adwp';
import { AdcmInputRbacPermissionModule } from '../../../shared/form-elements/adcm-input-rbac-permission/adcm-input-rbac-permission.module';
import { RbacPermissionFormModule } from '../permission-form/rbac-permission-form.module';
import { RbacRolesAsOptionsModule } from './options/rbac-roles-as-options.module';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';


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
    RbacRolesAsOptionsModule,
    MatFormFieldModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule
  ],
})
export class RbacRoleFormModule {
}
