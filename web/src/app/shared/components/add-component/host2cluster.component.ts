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
import { Component, OnDestroy, OnInit } from '@angular/core';
import { Host } from '@app/core/types';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

import { BaseFormDirective } from './base-form.directive';

@Component({
  selector: 'app-add-host2cluster',
  template: `
    <ng-container *ngIf="freeHost$ | async; else load">
      <div class="tools">
        <button
          mat-icon-button
          [ngClass]="{ hidden: !list.length }"
          (click)="showForm = !showForm"
          color="accent"
          matTooltip="Create and add new host"
        >
          <mat-icon>add_box</mat-icon>
        </button>
      </div>
      <div class="add-host2cluster">
        <div *ngFor="let host of list" class="full">
          <label>{{ host.name }}</label>
          <button mat-icon-button (click)="addHost2Cluster(host)" matTooltip="Host will be added to the cluster">
            <mat-icon color="primary">link</mat-icon>
          </button>
        </div>
      </div>
      <app-add-host *ngIf="showForm || !list.length" (cancel)="onCancel($event)" [noCluster]="true"></app-add-host>
    </ng-container>
    <ng-template #load><mat-spinner [diameter]="24"></mat-spinner></ng-template>
  `,
  styles: [
    '.tools {position: relative; height: 40px;} .tools>button { position: absolute; right: 0;}',
    '.full { display: flex;padding-left: 6px; margin: 3px 0; } .full>label { flex: 1 0 auto; vertical-align: middle; line-height: 40px; }',
    '.full:nth-child(odd) {background-color: #4e4e4e;}',
    '.full:hover {background-color: #5e5e5e; }'    
  ],
})
export class Host2clusterComponent extends BaseFormDirective implements OnInit, OnDestroy {
  freeHost$: Observable<Host[]>;
  list = [];
  showForm = false;

  ngOnInit() {
    this.freeHost$ = this.service.getFreeHosts().pipe(tap(list => (this.list = list)));
  }

  addHost2Cluster(host: Host) {
    this.service
      .addHostInCluster(host)
      .pipe(this.takeUntil())
      .subscribe(() => (this.list = this.list.filter(a => a.id !== host.id)));
  }
}
