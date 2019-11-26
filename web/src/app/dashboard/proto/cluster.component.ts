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
import { Component, EventEmitter, OnDestroy, OnInit } from '@angular/core';
import { ApiService } from '@app/core/api';
import { clearEmptyField, IButton, Widget } from '@app/core/types';
import { Cluster } from '@app/core/types/api';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { Observable, Subject } from 'rxjs';
import { filter, switchMap, takeUntil, tap } from 'rxjs/operators';

import { ChannelService } from '../channel.service';

@Component({
  selector: 'app-cluster-widget',
  styles: ['mat-list-item a {flex-grow: 1;}'],
  template: `
  <mat-accordion>
    <mat-expansion-panel [expanded]="!expanded" *ngIf="(cluster$ | async) as list">
    <mat-nav-list>
      <mat-list-item *ngFor="let cluster of list">
        <a [routerLink]="[ '/cluster', cluster.id ]">{{ cluster.name | uppercase }}</a>
        <button mat-icon-button color="primary" 
          (click)="viewCluster(cluster)" 
          matTooltip="Open details [ {{ cluster.name | uppercase }} ]"><mat-icon>open_in_browser</mat-icon></button>            
      </mat-list-item>
    </mat-nav-list>  
    <i *ngIf="list.length===0">Add a cluster.</i>
    </mat-expansion-panel>
    <mat-expansion-panel [expanded]="expanded">
      
    </mat-expansion-panel>
  </mat-accordion>

<button mat-icon-button *ngFor="let button of model.actions" matTooltip="{{ button.title }}" 
  [color]="button.color" 
  (click)="action(button)">
    <mat-icon>{{ button.icon }}</mat-icon>
</button>`,
})
export class ClusterComponent implements DynamicComponent, OnInit, OnDestroy {
  event = new EventEmitter<DynamicEvent>();
  model?: Widget;

  public expanded = false;
  cluster$: Observable<Cluster[]>;

  // @ViewChild(AddClusterComponent)
  // form: AddClusterComponent;

  destroy$ = new Subject();

  constructor(private api: ApiService, private channel: ChannelService) {}

  ngOnInit(): void {
    this.refresh();

    this.channel.stream$
      .pipe(
        takeUntil(this.destroy$),
        filter(data => data.cmd === 'stack_added'),
        // tap(() => (this.form.options$ = null))
      )
      .subscribe();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  send(data: Cluster) {
    this.api.root
      .pipe(
        switchMap(root => this.api.post<Cluster>(root.cluster, clearEmptyField(data))),
        tap(() => (this.expanded = false)),
        tap(() => (this.model.actions.find(a => a.name === 'addCluster').title = 'Add cluster')),
        tap(() => this.channel.emmitData({ cmd: 'cluster_added', row: null }))
      )
      .subscribe(() => this.refresh());
  }

  refresh() {
    this.cluster$ = this.api.root.pipe(switchMap(root => this.api.get<Cluster[]>(root.cluster)));
  }

  action(b: IButton) {
    this.event.emit({ name: b.name, data: b });
    if (b.name === 'addCluster') {
      this.expanded = !this.expanded;
      this.model.actions.find(a => a.name === 'addCluster').title = this.expanded ? 'Cancel' : 'Add cluster';
    }
  }

  viewCluster(cluster: Cluster) {
    this.channel.emmitData({ cmd: 'open_details', row: cluster });
  }
}
