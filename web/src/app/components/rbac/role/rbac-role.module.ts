import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRoleComponent } from './rbac-role.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { RbacRoleService } from './rbac-role.service';


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
  ],
  providers: [
    RbacRoleService,
  ],
})
export class RbacRoleModule {
}
