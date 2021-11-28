import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacUserComponent } from './rbac-user.component';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { ReactiveFormsModule } from '@angular/forms';


@NgModule({
  declarations: [
    RbacUserComponent
  ],
  exports: [
    RbacUserComponent
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule
  ]
})
export class RbacUserModule {
}
