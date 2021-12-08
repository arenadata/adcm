import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRoleComponent } from './rbac-role.component';
import { ReactiveFormsModule } from '@angular/forms';
import { RbacRoleService } from './rbac-role.service';
import { AdwpFormElementModule } from '@adwp-ui/widgets';


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
