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
import { RouterModule } from '@angular/router';
import { AuthGuard } from '@app/core';
import { SharedModule } from '@app/shared';

import { ActionsComponent } from './actions/actions.component';
import { StartComponent } from './start/start.component';
import { ConfigComponent } from './config.component';
import { MapComponent } from './map.component';

@NgModule({
  declarations: [StartComponent, ActionsComponent, ConfigComponent, MapComponent],
  imports: [
    CommonModule,
    SharedModule,
    RouterModule.forChild([
      {
        path: '',
        component: StartComponent,
        canActivate: [AuthGuard],
      },
      { path: ':id', component: StartComponent, canActivate: [AuthGuard] },
      { path: ':id/:step', component: StartComponent, canActivate: [AuthGuard] },
    ]),
  ],
  entryComponents: [],
})
export class WizardModule {}
