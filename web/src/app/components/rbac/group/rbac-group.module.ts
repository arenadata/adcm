import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacGroupComponent } from './rbac-group.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { RbacGroupService } from './rbac-group.service';
import { RbacUsersAsOptionsModule } from '../user/options/rbac-users-as-options.module';


@NgModule({
  declarations: [
    RbacGroupComponent,
  ],
  exports: [
    RbacGroupComponent,
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    RbacUsersAsOptionsModule,
  ],
  providers: [
    RbacGroupService,
  ],
})
export class RbacGroupModule {
}
