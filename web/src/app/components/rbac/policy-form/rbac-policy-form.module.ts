import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPolicyFormComponent } from './rbac-policy-form.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { AdwpFormElementModule } from '@adwp-ui/widgets';
import { RbacPolicyFormStepOneComponent } from './rbac-policy-form-step-one/rbac-policy-form-step-one.component';
import { RbacPolicyFormStepTwoComponent } from './rbac-policy-form-step-two/rbac-policy-form-step-two.component';
import { RbacPolicyFormStepThreeComponent } from './rbac-policy-form-step-three/rbac-policy-form-step-three.component';


@NgModule({
  declarations: [
    RbacPolicyFormComponent,
    RbacPolicyFormStepOneComponent,
    RbacPolicyFormStepTwoComponent,
    RbacPolicyFormStepThreeComponent
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
