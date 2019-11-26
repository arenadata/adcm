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
import { CommonModule } from '@angular/common';

import { SharedModule } from '@app/shared';
import { MainRoutingModule } from '@app/main/routing.module';

import { LoginComponent } from './login/login.component';
import { ProfileComponent } from './profile/profile.component';
import { SupportComponent } from './support/support.component';
import { TopComponent } from './top/top.component';
import { MessengerComponent } from './top/messenger/messenger.component';
import { ProgressComponent } from './progress.component';
import { PageNotFoundComponent, FatalErrorComponent, GatewayTimeoutComponent } from './server-status.component';

@NgModule({
  imports: [CommonModule, MainRoutingModule, SharedModule],
  declarations: [
    LoginComponent,
    ProfileComponent,
    SupportComponent,
    FatalErrorComponent,
    GatewayTimeoutComponent,
    PageNotFoundComponent,
    TopComponent,
    MessengerComponent,
    ProgressComponent,
  ],
  exports: [TopComponent, ProgressComponent],
  
})
export class MainModule {}
