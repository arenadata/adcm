import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRoleComponent } from './rbac-role.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';


@NgModule({
  declarations: [
    RbacRoleComponent
  ],
  exports: [
    RbacRoleComponent
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    AdwpFormElementModule
  ]
})
export class RbacRoleModule {
}
