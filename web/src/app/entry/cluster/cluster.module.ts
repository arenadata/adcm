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
import { AdwpListModule, AdwpUiWidgetsModule } from '@adwp-ui/widgets';

import { SharedModule, DetailComponent, MainInfoComponent, ConfigComponent, StatusComponent, ImportComponent } from '@app/shared';

import { ClusterListComponent } from './cluster.component';
import { HcmapComponent } from '@app/components/cluster/hcmap/hcmap.component';
import { HostComponent } from '@app/components/cluster/host/host.component';
import { ServicesComponent } from '@app/components/cluster/services/services.component';
import { AuthGuard } from '@app/core';
import { ActionCardComponent } from '@app/shared/components/actions/action-card/action-card.component';


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
      { path: 'status', component: StatusComponent },
      { path: 'import', component: ImportComponent },
      { path: 'action', component: ActionCardComponent },
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
      { path: 'status', component: StatusComponent },
      { path: 'import', component: ImportComponent },
      { path: 'action', component: ActionCardComponent },
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
    AdwpListModule.forRoot({
      itemsPerPage: [2, 10, 25, 50, 100],
    }),
  ],
  exports: [RouterModule],
})
export class ClusterRoutingModule {}

@NgModule({
  imports: [CommonModule, SharedModule, RouterModule, ClusterRoutingModule, AdwpUiWidgetsModule],
  declarations: [ClusterListComponent, ServicesComponent, HostComponent, HcmapComponent],
})
export class ClusterModule {}
