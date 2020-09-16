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
import { ApiBase, Cluster } from '@app/core/types/api';
import { Observable, of } from 'rxjs';
import { switchMap, tap, map } from 'rxjs/operators';

import { StatusService } from './status/status.service';
import { ComponentData } from './tooltip/tooltip.service';

@Component({
  selector: 'app-status-info',
  template: `
    <div *ngIf="statusInfo$ | async as components">
      <ng-container *ngIf="!components.length">Nothing to display</ng-container>
      <a [routerLink]="['/cluster', cluster.id, 'service', c.service_id, 'status']" *ngFor="let c of components" class="component">
        {{ (c.display_name || c.name || c.component_display_name || c.component).toUpperCase() }}&nbsp;<ng-container
          *ngTemplateOutlet="status; context: { status: c.status }"
        ></ng-container>
      </a>
      <ng-template #status let-status="status">
        <mat-icon *ngIf="status === 0" color="accent">check_circle_outline</mat-icon>
        <mat-icon *ngIf="status !== 0" color="warn">error_outline</mat-icon>
      </ng-template>
    </div>
  `,
  styles: ['mat-icon {vertical-align: middle;}', 'a.component {display: block; padding: 6px 8px;}'],
})
export class StatusInfoComponent implements OnInit {
  path: string;
  cluster: Cluster;
  current: ApiBase;
  statusInfo$: Observable<any>;

  constructor(private service: StatusService, private componentData: ComponentData) {}

  ngOnInit(): void {
    this.current = this.current || this.componentData.current;
    this.path = this.path || this.componentData.path;

    const [name] = this.path.split('/').reverse();

    let req$ = of([]);

    switch (name) {
      case 'cluster':
        this.cluster = this.current as Cluster;
        req$ = this.service.getServiceComponentsByCluster(this.cluster);
        break;
      case 'service':
        req$ = this.service.getClusterById((<any>this.current).cluster_id).pipe(
          tap((c) => (this.cluster = c)),
          switchMap((cluster) => this.service.getServiceComponentsByCluster(cluster, this.current.id))
        );
        break;
      case 'host':
        if ((<any>this.current).cluster_id)
          req$ = this.service.getClusterById((<any>this.current).cluster_id).pipe(
            tap((c) => (this.cluster = c)),
            switchMap((cluster) => this.service.getStatusInfo(cluster.id, cluster.hostcomponent).pipe(map((a) => this.service.getComponentsOnly(a, this.current.id))))
          );
        break;
    }

    this.statusInfo$ = req$.pipe(tap(() => this.componentData.emitter.emit('onLoad')));
  }
}
