import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPolicyComponent } from './rbac-policy.component';
import { ReactiveFormsModule } from '@angular/forms';
import { AdwpFormElementModule } from '../../../../../../../adwp_ui/projects/widgets/src/lib/form-element/form-element.module';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';


@NgModule({
  declarations: [
    RbacPolicyComponent
  ],
  exports: [
    RbacPolicyComponent
  ],
  imports: [
    CommonModule,
    AdwpFormElementModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatButtonModule,
  ]
})
export class RbacPolicyModule {
}
