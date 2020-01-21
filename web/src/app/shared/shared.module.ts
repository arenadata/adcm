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
  ActionsComponent,
  BaseListDirective,
  ButtonSpinnerComponent,
  CrumbsComponent,
  DetailComponent,
  DialogComponent,
  ExportComponent,
  ImportComponent,
  IssueInfoComponent,
  ListComponent,
  MainInfoComponent,
  StatusComponent,
  StatusInfoComponent,
  UpgradeComponent
} from './components';
import { ActionsDirective } from './components/actions/actions.directive';
import { SimpleTextComponent } from './components/tooltip';
import { ConfigurationModule } from './configuration/configuration.module';
import { DynamicDirective, HoverDirective, ScrollDirective } from './directives';
import { InfinityScrollDirective } from './directives/infinity-scroll.directive';
import { MultiSortDirective } from './directives/multi-sort.directive';
import { FormElementsModule } from './form-elements/form-elements.module';
import { MaterialModule } from './material.module';
import { BreakRowPipe, TagEscPipe } from './pipes';
import { StuffModule } from './stuff.module';
import { HostComponentsMapModule } from './host-components-map/host-components-map.module';

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
    HostComponentsMapModule
  ],
  declarations: [
    DetailComponent,
    DialogComponent,
    ListComponent,
    CrumbsComponent,
    BreakRowPipe,
    HoverDirective,
    DynamicDirective,
    ButtonSpinnerComponent,
    UpgradeComponent,
    ActionsDirective,
    ActionMasterComponent,
    TagEscPipe,
    IssueInfoComponent,
    SimpleTextComponent,
    BaseListDirective,
    StatusComponent,
    StatusInfoComponent,
    MainInfoComponent,
    ActionsComponent,
    ScrollDirective,
    MultiSortDirective,
    ImportComponent,
    ExportComponent,
    InfinityScrollDirective
  ],
  entryComponents: [DialogComponent, ActionMasterComponent, IssueInfoComponent, IssueInfoComponent, StatusInfoComponent, SimpleTextComponent],
  exports: [
    FormsModule,
    ReactiveFormsModule,
    MaterialModule,
    StuffModule,
    FormElementsModule,
    ConfigurationModule,
    AddingModule,
    HostComponentsMapModule,
    DetailComponent,
    DialogComponent,
    ListComponent,
    CrumbsComponent,
    BreakRowPipe,
    HoverDirective,
    DynamicDirective,
    ButtonSpinnerComponent,
    UpgradeComponent,
    ActionsDirective,
    TagEscPipe,
    BaseListDirective,
    StatusComponent,
    StatusInfoComponent,
    MainInfoComponent,
    ActionsComponent,
    ScrollDirective,
    ImportComponent,
    ExportComponent,
    InfinityScrollDirective
  ]
})
export class SharedModule {}
