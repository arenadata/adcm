import { Component, Input, Output, EventEmitter } from '@angular/core';
import { AdwpCellComponent, ILinkColumn, EventHelper } from '@app/adwp';

import { IHost } from '@app/models/host';
import { UniversalAdcmEventData } from '@app/models/universal-adcm-event-data';
import { ICluster } from '@app/models/cluster';

export interface AddClusterEventData extends UniversalAdcmEventData<IHost> {
  cluster: ICluster;
}

@Component({
  selector: 'app-cluster-column',
  template: `
    <ng-container *ngIf="row">
      <adwp-link-cell *ngIf="row?.cluster_id; else hasNoCluster"
                      [row]="row"
                      [column]="linkColumn"></adwp-link-cell>

      <ng-template #hasNoCluster>
        <mat-select appInfinityScroll (topScrollPoint)="getNextPageCluster($event)"
                    placeholder="Assign to cluster" class="select-in-cell" (click)="EventHelper.stopPropagation($event)"
                    (openedChange)="getClusters($event)"
                    (valueChange)="addCluster($event, clusters.value)" #clusters>
          <mat-option>...</mat-option>
          <mat-option *ngFor="let item of row.clusters" [value]="item.id">
            {{ item.title }}
          </mat-option>
        </mat-select>
      </ng-template>

    </ng-container>
  `,
  styles: [`
    :host {
      width: 100%;
    }
  `],
})
export class ClusterColumnComponent implements AdwpCellComponent<IHost> {

  EventHelper = EventHelper;

  @Input() row: IHost;

  @Output() onGetNextPageCluster = new EventEmitter<UniversalAdcmEventData<IHost>>();
  @Output() onGetClusters = new EventEmitter<UniversalAdcmEventData<IHost>>();
  @Output() onAddCluster = new EventEmitter<AddClusterEventData>();

  linkColumn: ILinkColumn<IHost> = {
    label: '',
    type: 'link',
    value: (row) => row.cluster_name,
    url: (row) => `/cluster/${row.cluster_id}`,
  };

  getNextPageCluster(event: MouseEvent) {
    this.onGetNextPageCluster.emit({ event, action: 'getNextPageCluster', row: this.row });
  }

  getClusters(event: MouseEvent) {
    this.onGetClusters.emit({ event, action: 'getClusters', row: this.row });
  }

  addCluster(event: MouseEvent, cluster: ICluster) {
    this.onAddCluster.emit({ event, action: 'addCluster', row: this.row, cluster });
  }

}
