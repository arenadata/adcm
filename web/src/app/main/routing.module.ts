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
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { AuthGuard } from '@app/core';
import { LogComponent } from '@app/ws-logs/log.component';

import { LoginComponent } from './login/login.component';
import { ProfileComponent } from './profile/profile.component';
import { FatalErrorComponent, GatewayTimeoutComponent, PageNotFoundComponent } from './server-status.component';
import { SupportComponent } from './support/support.component';

@NgModule({
  imports: [
    RouterModule.forChild([
      { path: '', redirectTo: 'admin', pathMatch: 'full' },
      { path: 'log', component: LogComponent, canActivate: [AuthGuard]  },
      { path: 'login', component: LoginComponent },
      { path: 'profile', component: ProfileComponent, canActivate: [AuthGuard] },
      { path: 'support', component: SupportComponent },
      { path: '404', component: PageNotFoundComponent },
      { path: '500', component: FatalErrorComponent },
      { path: '504', component: GatewayTimeoutComponent },
      {
        path: 'admin',
        loadChildren: () => import('app/admin/admin.module').then(m => m.AdminModule),
      },
      // {
      //   path: 'wizard',
      //   loadChildren: () => import('app/wizard/wizard.module').then(m => m.WizardModule),
      // },
      { path: '**', component: PageNotFoundComponent },
    ]),
  ],
  exports: [RouterModule],
})
export class MainRoutingModule {}
