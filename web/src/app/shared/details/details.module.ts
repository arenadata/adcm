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
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterModule } from '@angular/router';
import { AdwpListModule } from '@app/adwp';
import { StuffModule } from '../stuff.module';
import { SubtitleComponent } from './subtitle.component';
import { NavigationComponent } from '@app/components/navigation/navigation.component';
import { NavItemPipe } from '@app/pipes/nav-item.pipe';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ObjectLinkColumnPipe } from '@app/pipes/object-link-column.pipe';
import { SortObjectsPipe } from '@app/pipes/sort-objects.pipe';
import { TaskObjectsComponent } from '@app/components/columns/task-objects/task-objects.component';
import { HostDetailsComponent } from '@app/components/host/host-details/host-details.component';
import { LeftMenuComponent } from './left-menu/left-menu.component';
import { LabelMenuItemComponent } from './left-menu-items/label-menu-item/label-menu-item.component';
import { StatusMenuItemComponent } from './left-menu-items/status-menu-item/status-menu-item.component';
import { ProviderDetailsComponent } from '@app/components/hostprovider/provider-details/provider-details.component';
import { GroupConfigDetailsComponent } from '@app/components/hostprovider/group-config-details/group-config-details.component';
import { BundleDetailsComponent } from '@app/components/bundle/bundle-details/bundle-details.component';
import { ServiceDetailsComponent } from '@app/components/service/service-details/service-details.component';
import { ServiceComponentDetailsComponent } from '@app/components/service-component/service-component-details/service-component-details.component';
import { JobDetailsComponent } from '@app/components/job/job-details/job-details.component';
import { ClusterDetailsComponent } from '@app/components/cluster/cluster-details/cluster-details.component';
import { LogMenuItemComponent } from './left-menu-items/log-menu-item/log-menu-item.component';
import { ConcernMenuItemComponent } from '@app/shared/details/left-menu-items/concern-menu-item/concern-menu-item.component';
import { ConcernMenuItemPipe } from './left-menu-items/concern-menu-item/concern-menu-item.pipe';
import {
  MaintenanceModeButtonComponent
} from "@app/components/maintenance-mode-button/maintenance-mode-button.component";

@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    StuffModule,
    MatCardModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    AdwpListModule.forRoot({
      itemsPerPage: [10, 25, 50, 100],
    }),
  ],
  exports: [
    ServiceDetailsComponent,
    HostDetailsComponent,
    ProviderDetailsComponent,
    GroupConfigDetailsComponent,
    ServiceComponentDetailsComponent,
    ClusterDetailsComponent,
    BundleDetailsComponent,
    JobDetailsComponent,
    MaintenanceModeButtonComponent,
    ObjectLinkColumnPipe,
    SortObjectsPipe,
    AdwpListModule,
    TaskObjectsComponent,
  ],
  declarations: [
    ServiceDetailsComponent,
    HostDetailsComponent,
    ProviderDetailsComponent,
    GroupConfigDetailsComponent,
    ServiceComponentDetailsComponent,
    ClusterDetailsComponent,
    BundleDetailsComponent,
    JobDetailsComponent,
    SubtitleComponent,
    NavigationComponent,
    MaintenanceModeButtonComponent,
    NavItemPipe,
    ObjectLinkColumnPipe,
    SortObjectsPipe,
    TaskObjectsComponent,
    LeftMenuComponent,
    LabelMenuItemComponent,
    StatusMenuItemComponent,
    LogMenuItemComponent,
    ConcernMenuItemComponent,
    ConcernMenuItemPipe,
  ],
})
export class DetailsModule {}
