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
import { RouterModule, Routes } from '@angular/router';


import { ConfigComponent } from '../../shared/configuration/main/config.component';
import { ImportComponent, MainInfoComponent, StatusComponent } from '@app/shared/components';
import { SharedModule } from '@app/shared/shared.module';

import { ClusterListComponent } from './cluster.component';
import { HcmapComponent } from '@app/components/cluster/hcmap/hcmap.component';
import { ClusterHostComponent } from '../../components/cluster/host/cluster-host.component';
import { ServicesComponent } from '@app/components/cluster/services/services.component';
import { AuthGuard } from '../../core/auth/auth.guard';
import { ServiceComponentsComponent } from '../../components/service-component/service-components.component';
import {
  ConfigGroupHostListComponent,
  ConfigGroupListComponent,
  ConfigGroupModule
} from '../../config-groups';
import { ClusterDetailsComponent } from '../../components/cluster/cluster-details/cluster-details.component';
import { GroupConfigDetailsComponent } from '../../components/hostprovider/group-config-details/group-config-details.component';
import { ServiceDetailsComponent } from '../../components/service/service-details/service-details.component';
import { ServiceComponentDetailsComponent } from '../../components/service-component/service-component-details/service-component-details.component';
import { HostDetailsComponent } from '../../components/host/host-details/host-details.component';
import { ClusterStatusComponent } from '../../components/cluster/cluster-status/cluster-status.component';
import { ServiceStatusComponent } from '../../components/service/service-status/service-status.component';

const clusterRoutes: Routes = [
  {
    path: '',
    component: ClusterListComponent,
    canActivate: [AuthGuard],
  },
  {
    path: ':cluster',
    component: ClusterDetailsComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'service', component: ServicesComponent },
      { path: 'host', component: ClusterHostComponent },
      { path: 'host_component', component: HcmapComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_config', component: ConfigGroupListComponent },
      { path: 'status', component: ClusterStatusComponent },
      { path: 'import', component: ImportComponent },
    ],
  },
  {
    path: ':cluster/group_config/:group_config',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: GroupConfigDetailsComponent,
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },
  {
    path: ':cluster/service/:service',
    component: ServiceDetailsComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_config', component: ConfigGroupListComponent },
      { path: 'status', component: ServiceStatusComponent },
      { path: 'import', component: ImportComponent },
      { path: 'component', component: ServiceComponentsComponent },
    ],
  },
  {
    path: ':cluster/service/:service/group_config/:group_config',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: GroupConfigDetailsComponent,
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },
  {
    path: ':cluster/service/:service/component/:servicecomponent',
    component: ServiceComponentDetailsComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_config', component: ConfigGroupListComponent },
      { path: 'status', component: StatusComponent },
    ],
  },
  {
    path: ':cluster/service/:service/component/:component/group_config/:group_config',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: GroupConfigDetailsComponent,
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },
  {
    path: ':cluster/host/:host',
    component: HostDetailsComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'status', component: StatusComponent },
    ],
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(clusterRoutes),
  ],
  exports: [RouterModule],
})
export class ClusterRoutingModule {
}

@NgModule({
  imports: [
    CommonModule,
    SharedModule,
    RouterModule,
    ConfigGroupModule,
    ClusterRoutingModule,
  ],
  declarations: [
    ClusterListComponent,
    ServicesComponent,
    ClusterHostComponent,
    HcmapComponent,
    ClusterStatusComponent,
  ],
})
export class ClusterModule {}
