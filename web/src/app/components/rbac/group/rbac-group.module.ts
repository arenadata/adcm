import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacGroupComponent } from './rbac-group.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';


@NgModule({
  declarations: [
    RbacGroupComponent
  ],
  exports: [
    RbacGroupComponent
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    AdwpFormElementModule
  ]
})
export class RbacGroupModule {
}
