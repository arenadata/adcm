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
import { ActionListComponent } from './components/actions/action-list/action-list.component';
import { ActionsDirective } from './components/actions/actions.directive';
import { TooltipComponent } from './components/tooltip/tooltip.component';
import { TooltipDirective } from './components/tooltip/tooltip.directive';
import { BaseDirective, ForTestDirective, InfinityScrollDirective, MTextareaDirective, ScrollDirective, SocketListenerDirective } from './directives';
import { MaterialModule } from './material.module';
import { MenuItemComponent } from './components/actions/action-list/menu-item/menu-item.component';
import { CardItemComponent } from './components/actions/action-card/card-item/card-item.component';

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
    ScrollDirective,
    InfinityScrollDirective,
    ActionsComponent,
    ActionsDirective,
    ActionListComponent,
    MenuItemComponent,
    CardItemComponent,
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
    ScrollDirective,
    InfinityScrollDirective,
    ActionsComponent,
    ActionsDirective,
    ActionListComponent,
    MenuItemComponent,
    CardItemComponent,
  ],
})
export class StuffModule {}
