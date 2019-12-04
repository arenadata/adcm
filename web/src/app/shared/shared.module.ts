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

import {
  ActionMasterComponent,
  ActionsComponent,
  AddButtonComponent,
  AddFormComponent,
  BaseFormDirective,
  BaseListDirective,
  ButtonSpinnerComponent,
  ClusterComponent,
  CrumbsComponent,
  DetailComponent,
  DialogComponent,
  ExportComponent,
  Host2clusterComponent,
  HostComponent,
  ImportComponent,
  IssueInfoComponent,
  ListComponent,
  MainInfoComponent,
  Much2ManyComponent,
  ProviderComponent,
  ServiceComponent,
  ServiceHostComponent,
  StatusComponent,
  StatusInfoComponent,
  UpgradeComponent,
} from './components';
import { HolderDirective } from './components/hostmap/holder.directive';
import { ConfigurationModule } from './configuration/configuration.module';
import { DynamicDirective, HoverDirective, ScrollDirective } from './directives';
import { InfinityScrollDirective } from './directives/infinity-scroll.directive';
import { MultiSortDirective } from './directives/multi-sort.directive';
import { FormElementsModule } from './form-elements/form-elements.module';
import { MaterialModule } from './material.module';
import { BreakRowPipe, TagEscPipe } from './pipes';
import { StuffModule } from './stuff.module';
import { ActionsDirective } from './components/actions/actions.directive';
import { SimpleTextComponent } from './components/tooltip';

@NgModule({
  imports: [CommonModule, MaterialModule, FormsModule, ReactiveFormsModule, RouterModule, StuffModule, FormElementsModule, ConfigurationModule],
  declarations: [
    DetailComponent,
    DialogComponent,
    ListComponent,
    Much2ManyComponent,
    CrumbsComponent,
    BreakRowPipe,
    HoverDirective,
    DynamicDirective,
    ButtonSpinnerComponent,
    UpgradeComponent,
    ActionsDirective,
    ActionMasterComponent,
    ServiceHostComponent,
    TagEscPipe,
    IssueInfoComponent,
    SimpleTextComponent,
    AddButtonComponent,
    AddFormComponent,
    BaseListDirective,
    StatusComponent,
    StatusInfoComponent,
    ProviderComponent,
    ClusterComponent,
    HostComponent,
    ServiceComponent,
    Host2clusterComponent,
    BaseFormDirective,
    MainInfoComponent,
    ActionsComponent,
    ScrollDirective,
    HolderDirective,
    MultiSortDirective,
    ImportComponent,
    ExportComponent,
    InfinityScrollDirective,
  ],
  entryComponents: [
    DialogComponent,
    ActionMasterComponent,
    IssueInfoComponent,
    AddFormComponent,
    IssueInfoComponent,
    StatusInfoComponent,
    SimpleTextComponent
  ],
  exports: [
    FormsModule,
    ReactiveFormsModule,
    MaterialModule,
    StuffModule,
    FormElementsModule,
    ConfigurationModule,
    DetailComponent,
    DialogComponent,
    ListComponent,
    Much2ManyComponent,
    CrumbsComponent,
    BreakRowPipe,
    HoverDirective,
    DynamicDirective,
    ButtonSpinnerComponent,
    AddButtonComponent,
    UpgradeComponent,
    ActionsDirective,
    ServiceHostComponent,
    TagEscPipe,
    BaseListDirective,
    StatusComponent,
    StatusInfoComponent,
    ProviderComponent,
    ClusterComponent,
    HostComponent,
    ServiceComponent,
    Host2clusterComponent,
    BaseFormDirective,
    MainInfoComponent,
    ActionsComponent,
    ScrollDirective,
    ImportComponent,
    ExportComponent,
    InfinityScrollDirective,
  ],
})
export class SharedModule {}
