import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacPolicyFormComponent } from './rbac-policy-form.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { AdwpFilterPipeModule, AdwpFormElementModule, AdwpMapperPipeModule } from '@app/adwp';
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
import { GetParentsFromServicesPipe } from './rbac-policy-form-step-two/components/parametrized-by-service/get-clusters-from-services.pipe';
import { ParametrizedByClusterComponent } from './rbac-policy-form-step-two/components/parametrized-by-cluster/parametrized-by-cluster.component';
import { ParametrizedByServiceComponent } from './rbac-policy-form-step-two/components/parametrized-by-service/parametrized-by-service.component';
import { ParametrizedByProviderComponent } from './rbac-policy-form-step-two/components/parametrized-by-provider/parametrized-by-provider.component';
import { ParametrizedByDirective } from './rbac-policy-form-step-two/directives/parametrized-by.directive';
import { ParametrizedPipe } from './rbac-policy-form-step-two/pipes/parametrized.pipe';
import { ParametrizedByHostComponent } from './rbac-policy-form-step-two/components/parametrized-by-host/parametrized-by-host.component';


@NgModule({
  declarations: [
    RbacPolicyFormComponent,
    RbacPolicyFormStepOneComponent,
    RbacPolicyFormStepTwoComponent,
    RbacPolicyFormStepThreeComponent,
    GetParentsFromServicesPipe,
    ParametrizedByClusterComponent,
    ParametrizedByServiceComponent,
    ParametrizedByProviderComponent,
    ParametrizedByDirective,
    ParametrizedPipe,
    ParametrizedByHostComponent
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
