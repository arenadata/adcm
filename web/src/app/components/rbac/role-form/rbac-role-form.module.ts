import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRoleFormComponent } from './rbac-role-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '@adwp-ui/widgets';


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
  ],
})
export class RbacRoleFormModule {
}
