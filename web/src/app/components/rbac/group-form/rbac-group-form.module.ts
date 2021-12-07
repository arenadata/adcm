import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacGroupFormComponent } from './rbac-group-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { RbacUsersAsOptionsModule } from '../user-form/options/rbac-users-as-options.module';


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
  ],
})
export class RbacGroupFormModule {
}
