import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPolicyFormComponent } from './rbac-policy-form.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { AdwpFormElementModule, AdwpMapperPipeModule, AdwpFilterPipeModule } from '@adwp-ui/widgets';
import { RbacPolicyFormStepOneComponent } from './rbac-policy-form-step-one/rbac-policy-form-step-one.component';
import { RbacPolicyFormStepTwoComponent } from './rbac-policy-form-step-two/rbac-policy-form-step-two.component';
import { RbacPolicyFormStepThreeComponent } from './rbac-policy-form-step-three/rbac-policy-form-step-three.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { NgxMatSelectSearchModule } from 'ngx-mat-select-search';
import { RbacRolesAsOptionsModule } from '../role-form/options/rbac-roles-as-options.module';
import { FalseAsEmptyArrayModule } from '../../../shared/pipes/false-as-empty-array/false-as-empty-array.module';
import { RbacUsersAsOptionsModule } from '../user-form/options/rbac-users-as-options.module';
import { RbacGroupsAsOptionsModule } from '../group-form/options/rbac-groups-as-options.module';


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
    MatFormFieldModule,
    MatSelectModule,
    NgxMatSelectSearchModule,
    RbacRolesAsOptionsModule,
    AdwpMapperPipeModule,
    AdwpFilterPipeModule,
    FalseAsEmptyArrayModule,
    RbacUsersAsOptionsModule,
    RbacGroupsAsOptionsModule
  ]
})
export class RbacPolicyFormModule {
}
