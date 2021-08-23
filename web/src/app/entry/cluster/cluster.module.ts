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


import { DetailComponent } from '@app/shared/details/detail.component';
import { ConfigComponent } from '../../shared/configuration/main/config.component';
import { ImportComponent, MainInfoComponent, StatusComponent } from '@app/shared/components';
import { SharedModule } from '@app/shared/shared.module';

import { ClusterListComponent } from './cluster.component';
import { HcmapComponent } from '@app/components/cluster/hcmap/hcmap.component';
import { HostComponent } from '@app/components/cluster/host/host.component';
import { ServicesComponent } from '@app/components/cluster/services/services.component';
import { AuthGuard } from '../../core/auth/auth.guard';
import { ActionCardComponent } from '@app/shared/components/actions/action-card/action-card.component';
import { ServiceComponentsComponent } from '@app/components/service-components.component';
import {
  CONFIG_GROUP_LIST_SERVICE,
  ConfigGroupHostListComponent,
  ConfigGroupListComponent,
  ConfigGroupListService,
  ConfigGroupModule
} from '../../config-groups';


const clusterRoutes: Routes = [
  {
    path: '',
    component: ClusterListComponent,
    canActivate: [AuthGuard],
  },
  {
    path: ':cluster',
    component: DetailComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'service', component: ServicesComponent },
      { path: 'host', component: HostComponent },
      { path: 'host_component', component: HcmapComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_configs', component: ConfigGroupListComponent },
      { path: 'status', component: StatusComponent },
      { path: 'import', component: ImportComponent },
      { path: 'action', component: ActionCardComponent },
    ],
  },
  {
    path: ':cluster/group_configs/:group_configs',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: DetailComponent,
    data: {
      entityService: CONFIG_GROUP_LIST_SERVICE
    },
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },
  {
    path: ':cluster/service/:service',
    component: DetailComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_configs', component: ConfigGroupListComponent },
      { path: 'status', component: StatusComponent },
      { path: 'import', component: ImportComponent },
      { path: 'action', component: ActionCardComponent },
      { path: 'component', component: ServiceComponentsComponent },
    ],
  },
  {
    path: ':cluster/service/:service/group_configs/:group_configs',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: DetailComponent,
    data: {
      entityService: CONFIG_GROUP_LIST_SERVICE
    },
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },
  {
    path: ':cluster/service/:service/component/:servicecomponent',
    component: DetailComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_configs', component: ConfigGroupListComponent },
      { path: 'status', component: StatusComponent },
      { path: 'action', component: ActionCardComponent },
    ],
  },
  {
    path: ':cluster/service/:service/component/:servicecomponent/group_configs/:group_configs',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: DetailComponent,
    data: {
      entityService: CONFIG_GROUP_LIST_SERVICE
    },
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },
  {
    path: ':cluster/host/:host',
    component: DetailComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'status', component: StatusComponent },
      { path: 'action', component: ActionCardComponent },
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
  imports: [CommonModule, SharedModule, RouterModule, ConfigGroupModule, ClusterRoutingModule],
  declarations: [ClusterListComponent, ServicesComponent, HostComponent, HcmapComponent],
  providers: [
    {
      provide: CONFIG_GROUP_LIST_SERVICE,
      useClass: ConfigGroupListService
    },
  ]
})
export class ClusterModule {
}
