import { Component, ComponentRef } from '@angular/core';
import { IColumns, IListResult } from '@app/adwp';
import { Store } from '@ngrx/store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { TypeName } from '@app/core/types';
import { IHost } from '@app/models/host';
import { ListFactory } from '@app/factories/list.factory';
import { AddClusterEventData, ClusterColumnComponent } from '@app/components/columns/cluster-column/cluster-column.component';
import { UniversalAdcmEventData } from '@app/models/universal-adcm-event-data';
import { ConcernListDirective } from '@app/abstract-directives/concern-list.directive';
import { ConcernEventType } from '@app/models/concern/concern-reason';
import { ICluster } from '@app/models/cluster';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { ConcernService } from '@app/services/concern.service';
import { HostService } from '@app/services/host.service';
import { ApiService } from '@app/core/api';

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
  styleUrls: ['./host-list.component.scss'],
})
export class HostListComponent extends ConcernListDirective<IHost> {

  type: TypeName = 'host';
  eventTypes = [ConcernEventType.Host];

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
            if (data?.cluster) {
              this.hostService.addToCluster(data.row.id, data.cluster as any as number)
                .subscribe((host) => {
                  if (this.data$?.value?.results) {
                    this.api.getOne('cluster', host.cluster_id).subscribe((cluster: ICluster) => {
                      const tableData = Object.assign({}, this.data$.value);
                      const index = tableData.results.findIndex(item => item.id === host.id);
                      const row = Object.assign({}, tableData.results[index]);

                      row.cluster_id = cluster.id;
                      row.cluster_name = cluster.name;

                      tableData.results.splice(index, 1, row);
                      this.reload(tableData as IListResult<any>);
                    });
                  }
                });
            }
          });
      }
    },
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsButton(this),
    ListFactory.configColumn(this),
    ListFactory.maintenanceModeColumn(this, 'host'),
    ListFactory.deleteColumn(this),
  ] as IColumns<IHost>;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected concernService: ConcernService,
    protected hostService: HostService,
    protected api: ApiService,
  ) {
    super(service, store, route, router, dialog, concernService);
  }
}
