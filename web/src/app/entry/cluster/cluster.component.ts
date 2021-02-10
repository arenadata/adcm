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
import { Component, OnInit } from '@angular/core';
import { ClusterService } from '@app/core';
import { BehaviorSubject } from 'rxjs';
import { IColumn, IListResult } from '@adwp-ui/widgets';

import { ICluster } from '../../models/cluster';
import { StatusColumnComponent } from '../../components/status-column/status-column.component';
import { ActionsColumnComponent } from '../../components/actions-column/actions-column.component';
import { StateColumnComponent } from '../../components/state-column/state-column.component';
import { UpgradeComponent } from '../../shared';

@Component({
  selector: 'app-cluster-host',
  template: `
    <app-add-button [name]="'host2cluster'" class="add-button">Add hosts</app-add-button>
    <app-list class="main" [appBaseList]="'host2cluster'"></app-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:fixed; right: 20px;top:120px;}'],
})
export class HostComponent {}

@Component({
  selector: 'app-services',
  template: `
    <app-add-button [name]="'service'" class="add-button">Add services</app-add-button>
    <app-list class="main" [appBaseList]="'service2cluster'" appActionHandler></app-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:fixed; right: 20px;top:120px;}'],
})
export class ServicesComponent {}

@Component({
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/cluster', title: 'clusters' }]"></app-crumbs>
      <app-add-button [name]="typeName" (added)="list.current = $event">Create {{ typeName }}</app-add-button>
    </mat-toolbar>
    <app-list #list appActionHandler [appBaseList]="typeName" (reload)="reload($event)"></app-list>

    <br>
    <br>

    <adwp-list [columns]="columns" [dataSource]="data$ | async"></adwp-list>
  `,
  styles: [`
    :host { flex: 1; }
  `],
})
export class ClusterListComponent {

  typeName = 'cluster';

  data$: BehaviorSubject<IListResult<ICluster>> = new BehaviorSubject(null);

  columns = [
    {
      label: 'Name',
      sort: 'name',
      value: (row) => row.display_name || row.name,
    },
    {
      label: 'Bundle',
      sort: 'prototype_version',
      value: (row) => [row.prototype_display_name || row.prototype_name, row.prototype_version, row.edition].join(' '),
    },
    {
      label: 'Description',
      sort: 'description',
      value: (row) => row.description,
    },
    {
      label: 'State',
      sort: 'state',
      type: 'component',
      className: 'width100',
      headerClassName: 'width100',
      component: StateColumnComponent,
    },
    {
      label: 'Status',
      sort: 'status',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: StatusColumnComponent,
    },
    {
      label: 'Actions',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: ActionsColumnComponent,
    },
    {
      label: 'Import',
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'import_export',
        callback: (row) => console.log(row),
      }]
    },
    {
      label: 'Upgrade',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: UpgradeComponent,
    },
    {
      label: 'Config',
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'settings',
        callback: (row) => console.log(row),
      }]
    },
    {
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'delete',
        callback: (row) => console.log(row),
      }]
    },
  ] as IColumn<ICluster>;

  reload(data: IListResult<ICluster>) {
    console.log(data);
    this.data$.next(data);
  }

}

@Component({
  template: ` <app-service-host [cluster]="cluster"></app-service-host> `,
  styles: [':host { flex: 1; }'],
})
export class HcmapComponent implements OnInit {
  cluster: { id: number; hostcomponent: string };
  constructor(private service: ClusterService) {}

  ngOnInit() {
    const { id, hostcomponent } = { ...this.service.Cluster };
    this.cluster = { id, hostcomponent };
  }
}
