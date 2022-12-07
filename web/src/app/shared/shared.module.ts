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
import { TranslateModule } from '@ngx-translate/core';
import { MatTreeModule } from '@angular/material/tree';
import { AddingModule } from './add-component/adding.module';
import { UpgradeMasterComponent } from "@app/shared/components/upgrades/master/master.component";
import {
  ActionMasterComponent,
  ButtonSpinnerComponent,
  DialogComponent,
  ExportComponent,
  ImportComponent,
  IssueInfoComponent,
  MainInfoComponent,
  StatusInfoComponent,
  UpgradeComponent,
} from './components';
import { ActionMasterConfigComponent } from './components/actions/master/action-master-config.component';
import { MultiSortDirective } from './components/list/multi-sort.directive';
import { ConfigurationModule } from './configuration/configuration.module';
import { DetailsModule } from './details/details.module';
import { HoverDirective } from './directives';
import { FormElementsModule } from './form-elements/form-elements.module';
import { HostComponentsMapModule } from './host-components-map/host-components-map.module';
import { MaterialModule } from './material.module';
import { BreakRowPipe, TagEscPipe } from './pipes';
import { StuffModule } from './stuff.module';
import { StatusColumnComponent } from '@app/components/columns/status-column/status-column.component';
import { StateColumnComponent } from '@app/components/columns/state-column/state-column.component';
import { EditionColumnComponent } from '@app/components/columns/edition-column/edition-column.component';
import { ClusterColumnComponent } from '@app/components/columns/cluster-column/cluster-column.component';
import { ServiceComponentsComponent } from '@app/components/service-component/service-components.component';
import { JobService } from '@app/services/job.service';
import { TaskService } from '@app/services/task.service';
import { ToDataSourcePipe } from '@app/pipes/to-data-source.pipe';
import { PickKeysPipe } from '@app/pipes/pick-keys.pipe';
import { TranslateKeysPipe } from '@app/pipes/translate-object-keys.pipe';
import { TooltipModule } from '@app/shared/components/tooltip/tooltip.module';
import { StatusTreeComponent } from '@app/components/status-tree/status-tree.component';
import { HostStatusComponent } from '@app/components/host/host-status/host-status.component';
import { EntityStatusToStatusTreePipe } from '@app/pipes/entity-status-to-status-tree.pipe';
import { ServiceStatusComponent } from '@app/components/service/service-status/service-status.component';
import { ServiceComponentStatusComponent } from '@app/components/service-component/service-component-status/service-component-status.component';
import { StatusTreeLinkPipe } from '@app/pipes/status-tree-link.pipe';
import { RbacUserService } from '@app/services/rbac-user.service';
import { RbacGroupService } from '@app/services/rbac-group.service';
import { RbacRoleService } from '@app/services/rbac-role.service';
import { RbacPolicyService } from '@app/services/rbac-policy.service';
import { DynamicModule } from '@app/shared/directives/dynamic/dynamic.module';
import { RbacObjectCandidateService } from '@app/services/rbac-object-candidate.service';
import { UpgradeMasterConfigComponent } from "@app/shared/components/upgrades/master/upgrade-master-config.component";
import { RbacAuditOperationsService } from "@app/services/rbac-audit-operations.service";
import { HistoryColumnComponent } from "@app/components/columns/history-column/history-column.component";
import { WrapperColumnComponent } from "@app/components/columns/wrapper-column/wrapper-column.component";
import {
  DownloadButtonColumnComponent
} from "@app/components/columns/download-button-column/download-button-column.component";
import { RbacAuditLoginService } from "@app/services/rbac-audit-login.service";

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
    TranslateModule,
    TooltipModule,
    MatTreeModule,
    DynamicModule,
  ],
  declarations: [
    DialogComponent,
    BreakRowPipe,
    HoverDirective,
    ButtonSpinnerComponent,
    TagEscPipe,
    IssueInfoComponent,
    HostStatusComponent,
    ServiceStatusComponent,
    StatusInfoComponent,
    MainInfoComponent,
    MultiSortDirective,
    ImportComponent,
    ExportComponent,
    ActionMasterComponent,
    ActionMasterConfigComponent,
    UpgradeMasterComponent,
    UpgradeMasterConfigComponent,
    StatusColumnComponent,
    StateColumnComponent,
    EditionColumnComponent,
    ClusterColumnComponent,
    ServiceComponentsComponent,
    ServiceComponentStatusComponent,
    ToDataSourcePipe,
    PickKeysPipe,
    TranslateKeysPipe,
    StatusTreeComponent,
    EntityStatusToStatusTreePipe,
    StatusTreeLinkPipe,
    HistoryColumnComponent,
    WrapperColumnComponent,
    DownloadButtonColumnComponent,
  ],
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
    BreakRowPipe,
    HoverDirective,
    ButtonSpinnerComponent,
    UpgradeComponent,
    TagEscPipe,
    HostStatusComponent,
    ServiceStatusComponent,
    StatusInfoComponent,
    MainInfoComponent,
    ImportComponent,
    ExportComponent,
    StatusColumnComponent,
    StateColumnComponent,
    EditionColumnComponent,
    ClusterColumnComponent,
    ServiceComponentsComponent,
    ServiceComponentStatusComponent,
    ToDataSourcePipe,
    PickKeysPipe,
    TranslateKeysPipe,
    TooltipModule,
    StatusTreeComponent,
    EntityStatusToStatusTreePipe,
    StatusTreeLinkPipe,
    HistoryColumnComponent,
    WrapperColumnComponent,
    DownloadButtonColumnComponent,
  ],
  providers: [
    JobService,
    TaskService,
    RbacUserService,
    RbacGroupService,
    RbacRoleService,
    RbacPolicyService,
    RbacAuditOperationsService,
    RbacAuditLoginService,
    RbacObjectCandidateService,
  ],
})
export class SharedModule {}
