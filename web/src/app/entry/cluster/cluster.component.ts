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
import { Component, ComponentRef, OnInit } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { IColumns, IListResult, Paging, RowEventData } from '@adwp-ui/widgets';
import { Sort } from '@angular/material/sort';
import { PageEvent } from '@angular/material/paginator';

import { ICluster } from '@app/models/cluster';
import { StatusColumnComponent } from '@app/components/columns/status-column/status-column.component';
import { ActionsColumnComponent } from '@app/components/columns/actions-column/actions-column.component';
import { StateColumnComponent } from '@app/components/columns/state-column/state-column.component';
import { UpgradeComponent } from '@app/shared';
import { ListDirective } from '@app/abstract-directives/list.directive';
import { Entities, TypeName } from '../../core/types';
import { AdwpBaseListDirective } from '../../abstract-directives/adwp-base-list.directive';

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
export class ClusterListComponent extends ListDirective implements OnInit {

  type: TypeName = 'cluster';

  data$: BehaviorSubject<IListResult<ICluster>> = new BehaviorSubject(null);

  defaultSort: Sort = { active: 'id', direction: 'desc' };

  listColumns = [
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
      instanceTaken: (componentRef: ComponentRef<StatusColumnComponent<ICluster>>) => {
        componentRef.instance.onClick
          .pipe(this.takeUntil())
          .subscribe((data) => this.gotoStatus(data));
      }
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
        callback: (row) => this.baseListDirective.listEvents({ cmd: 'import', row }),
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
        callback: (row) => this.baseListDirective.listEvents({ cmd: 'config', row }),
      }]
    },
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

  paging: BehaviorSubject<Paging> = new BehaviorSubject<Paging>(null);
  sorting: BehaviorSubject<Sort> = new BehaviorSubject<Sort>(null);

  ngOnInit() {
    this.baseListDirective = new AdwpBaseListDirective(this, this.service, this.store);
    this.baseListDirective.typeName = this.type;
    this.baseListDirective.reload = this.reload.bind(this);
    (this.baseListDirective as AdwpBaseListDirective).paging = this.paging;
    (this.baseListDirective as AdwpBaseListDirective).sorting = this.sorting;
    this.baseListDirective.init();
  }

  reload(data: IListResult<Entities>) {
    this.data$.next(data as any);
  }

  clickRow(data: RowEventData) {
    this.clickCell(data.event, 'title', data.row);
  }

  auxclickRow(data: RowEventData) {
    this.clickCell(data.event, 'new-tab', data.row);
  }

  changeCount(count: number) {}

  getPageIndex(): number {
    return this.paging.value.pageIndex - 1;
  }

  getPageSize(): number {
    return this.paging.value.pageSize;
  }

  onChangePaging(paging: Paging): void {
    this.paging.next(paging);

    const pageEvent = new PageEvent();
    pageEvent.pageIndex = this.getPageIndex();
    pageEvent.length = this.data$.value.count;
    pageEvent.pageSize = this.getPageSize();

    this.pageHandler(pageEvent);
  }

  onChangeSort(sort: Sort): void {
    this.sorting.next(sort);
    this.changeSorting(sort);
  }

  getSort(): Sort {
    return this.sorting.value;
  }

}

