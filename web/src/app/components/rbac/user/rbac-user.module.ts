import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacUserComponent } from './rbac-user.component';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { ReactiveFormsModule } from '@angular/forms';
import { RbacUserService } from './rbac-user.service';
import { RbacGroupModule } from '../group/rbac-group.module';
import { RbacGroupsAsOptionsModule } from '../group/options/rbac-groups-as-options.module';


@NgModule({
  declarations: [
    RbacUserComponent,
  ],
  exports: [
    RbacUserComponent,
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    RbacGroupModule,
    RbacGroupsAsOptionsModule
  ],
  providers: [RbacUserService]
})
export class RbacUserModule {
}
