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
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { AddingModule } from './add-component/adding.module';
import {
  ActionMasterComponent,
  ButtonSpinnerComponent,
  DialogComponent,
  ExportComponent,
  ImportComponent,
  IssueInfoComponent,
  MainInfoComponent,
  StatusComponent,
  StatusInfoComponent,
  UpgradeComponent,
} from './components';
import { ActionCardComponent } from './components/actions/action-card/action-card.component';
import { ActionMasterConfigComponent } from './components/actions/master/action-master-config.component';
import { BaseListDirective } from './components/list/base-list.directive';
import { ListComponent } from './components/list/list.component';
import { MultiSortDirective } from './components/list/multi-sort.directive';
import { SimpleTextComponent } from './components/tooltip';
import { ConfigurationModule } from './configuration/configuration.module';
import { DetailsModule } from './details/details.module';
import { DynamicDirective, HoverDirective } from './directives';
import { FormElementsModule } from './form-elements/form-elements.module';
import { HostComponentsMapModule } from './host-components-map/host-components-map.module';
import { MaterialModule } from './material.module';
import { BreakRowPipe, TagEscPipe } from './pipes';
import { StuffModule } from './stuff.module';

@NgModule({
  imports: [
    CommonModule,
    MaterialModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    StuffModule,
    FormElementsModule,
    ConfigurationModule,
    AddingModule,
    HostComponentsMapModule,
    DetailsModule,
  ],
  declarations: [
    DialogComponent,
    ListComponent,
    BreakRowPipe,
    HoverDirective,
    DynamicDirective,
    ButtonSpinnerComponent,
    TagEscPipe,
    IssueInfoComponent,
    SimpleTextComponent,
    BaseListDirective,
    StatusComponent,
    StatusInfoComponent,
    MainInfoComponent,
    MultiSortDirective,
    ImportComponent,
    ExportComponent,
    ActionMasterComponent,
    ActionMasterConfigComponent,
    ActionCardComponent,
  ],
  // entryComponents: [DialogComponent, IssueInfoComponent, IssueInfoComponent, StatusInfoComponent, SimpleTextComponent, ActionMasterComponent],
  exports: [
    FormsModule,
    ReactiveFormsModule,
    MaterialModule,
    StuffModule,
    FormElementsModule,
    ConfigurationModule,
    AddingModule,
    HostComponentsMapModule,
    DetailsModule,
    DialogComponent,
    ListComponent,
    BreakRowPipe,
    HoverDirective,
    DynamicDirective,
    ButtonSpinnerComponent,
    UpgradeComponent,
    TagEscPipe,
    BaseListDirective,
    StatusComponent,
    StatusInfoComponent,
    MainInfoComponent,
    ImportComponent,
    ExportComponent,
    ActionCardComponent,
  ],
})
export class SharedModule {}
