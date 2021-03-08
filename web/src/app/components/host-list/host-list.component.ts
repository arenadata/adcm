import { Component, ComponentRef } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { IHost } from '@app/models/host';
import { ListFactory } from '@app/factories/list-factory';
import { AddClusterEventData, ClusterColumnComponent } from '@app/components/columns/cluster-column/cluster-column.component';
import { UniversalAdcmEventData } from '@app/models/universal-adcm-event-data';

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
      type: 'component',
      label: 'Cluster',
      sort: 'cluster_name',
      component: ClusterColumnComponent,
      instanceTaken: (componentRef: ComponentRef<ClusterColumnComponent>) => {
        componentRef.instance
          .onGetNextPageCluster
          .pipe(this.takeUntil())
          .subscribe((data: UniversalAdcmEventData<IHost>) => {
            this.clickCell(data.event, data.action, data.row);
          });

        componentRef.instance
          .onGetClusters
          .pipe(this.takeUntil())
          .subscribe((data: UniversalAdcmEventData<IHost>) => {
            this.clickCell(data.event, data.action, data.row);
          });

        componentRef.instance
          .onAddCluster
          .pipe(this.takeUntil())
          .subscribe((data: AddClusterEventData) => {
            this.clickCell(data.event, data.action, data.row, data.cluster);
          });
      }
    },
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this.takeUntil.bind(this), this.gotoStatus.bind(this)),
    ListFactory.actionsColumn(),
    ListFactory.configColumn(this),
    ListFactory.deleteColumn(this),
  ] as IColumns<IHost>;

}
