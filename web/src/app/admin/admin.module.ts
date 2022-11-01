// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '@app/core/auth/auth.guard';
import { IntroComponent } from './intro.component';
import { PatternComponent } from './pattern.component';
import { SettingsComponent } from './settings.component';
import { UsersComponent } from './users/users.component';
import { RbacGroupFormModule } from '../components/rbac/group-form/rbac-group-form.module';
import { RbacUserFormModule } from '../components/rbac/user-form/rbac-user-form.module';
import { RbacRoleFormModule } from '../components/rbac/role-form/rbac-role-form.module';
import { GroupsComponent } from './groups/groups.component';
import { RolesComponent } from './roles/roles.component';
import { PoliciesComponent } from './policies/policies.component';
import { AuditOperationsComponent } from './audit-operations/audit-operations.component';
import { AdwpListModule } from '@adwp-ui/widgets';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatCardModule } from '@angular/material/card';
import { StuffModule } from '../shared/stuff.module';
import { AddingModule } from '../shared/add-component/adding.module';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RbacPolicyFormModule } from '../components/rbac/policy-form/rbac-policy-form.module';
import { ConfigurationModule } from '../shared/configuration/configuration.module';
import {
  RbacAuditOperationsHistoryFormComponent
} from "../components/rbac/audit-operations-history-form/rbac-audit-operations-history-form.component";

const routes: Routes = [
  {
    path: '',
    component: PatternComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      {
        path: '',
        redirectTo: 'intro',
        pathMatch: 'full',
      },
      {
        path: 'intro',
        component: IntroComponent,
      },
      {
        path: 'settings',
        component: SettingsComponent,
      },
      {
        path: 'users',
        component: UsersComponent,
      },
      {
        path: 'groups',
        component: GroupsComponent,
      },
      {
        path: 'roles',
        component: RolesComponent,
      },
      {
        path: 'policies',
        component: PoliciesComponent,
      },
      {
        path: 'audit/operations',
        component: AuditOperationsComponent,
      }
    ],
  },
];

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
    AdwpListModule,
    RbacGroupFormModule,
    RbacRoleFormModule,
    RbacUserFormModule,
    RbacPolicyFormModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatCardModule,
    StuffModule,
    AddingModule,
    MatButtonModule,
    MatIconModule,
    ConfigurationModule
  ],
  declarations: [
    IntroComponent,
    SettingsComponent,
    UsersComponent,
    PatternComponent,
    GroupsComponent,
    RolesComponent,
    PoliciesComponent,
    AuditOperationsComponent,
    RbacAuditOperationsHistoryFormComponent
  ],
})
export class AdminModule {
}
