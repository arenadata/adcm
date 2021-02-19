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
import { IColumns } from '@adwp-ui/widgets';

import { ICluster } from '@app/models/cluster';
import { UpgradeComponent } from '@app/shared';
import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { ListFactory } from '../../factories/list-factory';

@Component({
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/cluster', title: 'clusters' }]"></app-crumbs>
      <app-add-button [name]="type" (added)="list.current = $event">Create {{ type }}</app-add-button>
    </mat-toolbar>
    <app-list #list [type]="type"></app-list>

    <br>
    <br>

    <adwp-list
      [columns]="listColumns"
      [dataSource]="data$ | async"
      [paging]="paging | async"
      [sort]="sorting | async"
      [defaultSort]="defaultSort"
      [currentId]="current ? current.id : undefined"
      (clickRow)="clickRow($event)"
      (auxclickRow)="auxclickRow($event)"
      (changePaging)="onChangePaging($event)"
      (changeSort)="onChangeSort($event)"
    ></adwp-list>
  `,
  styles: [`
    :host { flex: 1; }
  `],
})
export class ClusterListComponent extends AdwpListDirective<ICluster> implements OnInit {

  type: TypeName = 'cluster';

  listColumns = [
    ListFactory.nameColumn(),
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
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this.takeUntil.bind(this), this.gotoStatus.bind(this)),
    ListFactory.actionsColumn(),
    ListFactory.importColumn(this),
    {
      label: 'Upgrade',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: UpgradeComponent,
    },
    ListFactory.configColumn(this),
    {
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'delete',
        callback: (row, event) => this.delete(event, row),
      }]
    },
  ] as IColumns<ICluster>;

}

