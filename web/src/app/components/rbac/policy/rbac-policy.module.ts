import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPolicyComponent } from './rbac-policy.component';
import { ReactiveFormsModule } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { AdwpFormElementModule } from '@adwp-ui/widgets';


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
