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

import { ActionsComponent, CrumbsComponent, UpgradeComponent } from './components';
import { ActionsDirective } from './components/actions/actions.directive';
import { TooltipComponent } from './components/tooltip/tooltip.component';
import { TooltipDirective } from './components/tooltip/tooltip.directive';
import { BaseDirective, ForTestDirective, MTextareaDirective, ScrollDirective, SocketListenerDirective, InfinityScrollDirective } from './directives';
import { MaterialModule } from './material.module';

@NgModule({
  declarations: [
    ForTestDirective,
    TooltipDirective,
    TooltipComponent,
    MTextareaDirective,
    BaseDirective,
    SocketListenerDirective,
    CrumbsComponent,
    UpgradeComponent,
    ActionsComponent,
    ActionsDirective,
    ScrollDirective,
    InfinityScrollDirective
  ],
  imports: [CommonModule, MaterialModule, RouterModule],
  exports: [
    ForTestDirective,
    TooltipDirective,
    TooltipComponent,
    MTextareaDirective,
    BaseDirective,
    SocketListenerDirective,
    CrumbsComponent,
    UpgradeComponent,
    ActionsComponent,
    ActionsDirective,
    ScrollDirective,
    InfinityScrollDirective
  ]
})
export class StuffModule {}
