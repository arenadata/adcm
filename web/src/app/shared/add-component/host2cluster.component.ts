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
import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { Host } from '@app/core/types';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

import { BaseFormDirective } from './base-form.directive';
import { HostComponent } from './host.component';

@Component({
  selector: 'app-add-host2cluster',
  template: `
    <ng-container *ngIf="freeHost$ | async; else load">
      <div class="tools" [ngClass]="{ hidden: !list.length }">
        <mat-select
          class="add-host2cluster"
          appInfinityScroll
          (topScrollPoint)="nextPage()"
          (valueChange)="addHost2Cluster(free.value)"
          #free
          placeholder="Select free host and assign to cluster"
        >
          <mat-option>...</mat-option>
          <mat-option *ngFor="let host of list" [value]="host.id" [appTooltip]="host.fqdn" [appTooltipShowByCondition]="true">{{ host.fqdn }}</mat-option>
        </mat-select>

        <button
          mat-icon-button
          (click)="showForm = !showForm"
          [color]="showForm ? 'primary' : 'accent'"
          [matTooltip]="showForm ? 'Hide host creation form' : 'Create and add new host'"
        >
          <mat-icon>{{ showForm ? 'clear' : 'add' }}</mat-icon>
        </button>
      </div>

      <ng-container *ngIf="showForm || !list.length">
        <app-add-host #form (cancel)="onCancel($event)" [noCluster]="true"></app-add-host>
        <p class="controls">
          <button mat-raised-button [disabled]="!form.form.valid" color="accent" (click)="save(form.form.value)">Save</button>
          <button mat-raised-button color="primary" (click)="onCancel()">Cancel</button>
        </p>
      </ng-container>
    </ng-container>
    <ng-template #load><mat-spinner [diameter]="24"></mat-spinner></ng-template>
  `,
  styles: [
    '.tools { display: flex; align-items: baseline; margin: 0 -2px 10px; }',
    '.full { display: flex;padding-left: 6px; margin: 3px 0; justify-content: space-between; } .full>label { vertical-align: middle; line-height: 40px; }',
    '.full:nth-child(odd) {background-color: #4e4e4e;}',
    '.full:hover {background-color: #5e5e5e; }',
    '.add-host2cluster { flex: 1; }'
  ]
})
export class Host2clusterComponent extends BaseFormDirective implements OnInit, OnDestroy {
  freeHost$: Observable<Host[]>;
  list = [];
  showForm = false;

  page = 0;
  limit = 10;

  @ViewChild('form') hostForm: HostComponent;

  ngOnInit() {
    this.freeHost$ = this.service
      .getList<Host>('host', { limit: this.limit, page: this.page, cluster_is_null: 'true' })
      .pipe(tap(list => (this.list = list)));
  }

  save(host: Host) {
    host.cluster_id = this.service.Cluster.id;
    this.service
      .addHost(host)
      .pipe(
        this.takeUntil(),
        tap(() => this.hostForm.form.controls['fqdn'].setValue(''))
      )
      .subscribe();
  }

  addHost2Cluster(id: number) {
    if (id)
      this.service
        .addHostInCluster(id)
        .pipe(this.takeUntil())
        .subscribe(() => (this.list = this.list.filter(a => a.id !== id)));
  }

  nextPage() {
    const count = this.list.length;
    if (count === (this.page + 1) * this.limit) {
      this.page++;
      this.service
        .getList<Host>('host', { limit: this.limit, page: this.page, cluster_is_null: 'true' })
        .pipe(this.takeUntil())
        .subscribe(list => (this.list = [...this.list, ...list]));
    }
  }
}
