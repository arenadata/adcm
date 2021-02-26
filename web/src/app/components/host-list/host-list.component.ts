import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { IHost } from '@app/models/host';
import { ListFactory } from '@app/factories/list-factory';

@Component({
  selector: 'app-host-list',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/host', title: 'hosts' }]"></app-crumbs>
      <app-add-button [name]="type" (added)="current = $event">Create {{ type }}</app-add-button>
    </mat-toolbar>

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
  styles: [':host { flex: 1; }'],
})
export class HostListComponent extends AdwpListDirective<IHost> {

  type: TypeName = 'host';

  listColumns = [
    ListFactory.fqdnColumn(),
    ListFactory.providerColumn(),
    {
      type: 'link',
      label: 'Cluster',
      sort: 'cluster_name',
      value: (row) => row.cluster_name,
      url: (row) => `/cluster/${row.cluster_id}`,
    },
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this.takeUntil.bind(this), this.gotoStatus.bind(this)),
    ListFactory.actionsColumn(),
    ListFactory.configColumn(this),
    ListFactory.deleteColumn(this),
  ] as IColumns<IHost>;

}
