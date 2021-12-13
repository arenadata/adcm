import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPolicyFormComponent } from './rbac-policy-form.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { AdwpFormElementModule } from '@adwp-ui/widgets';


@NgModule({
  declarations: [
    RbacPolicyFormComponent
  ],
  exports: [
    RbacPolicyFormComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatButtonModule,
    AdwpFormElementModule,
  ]
})
export class RbacPolicyFormModule {
}
