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
import { MatSelectionList, MatSelectionListChange, MatListOption } from '@angular/material/list';
import { openClose } from '@app/core/animations';
import { Host } from '@app/core/types';
import { Observable } from 'rxjs';
import { tap, switchMap } from 'rxjs/operators';

import { BaseFormDirective } from './base-form.directive';
import { HostComponent } from './host.component';

@Component({
  selector: 'app-add-host2cluster',
  template: `
    <ng-container *ngIf="freeHost$ | async as list; else load">
      <div [style.overflow]="'hidden'" [@openClose]="showForm || !list.length">
        <app-add-host #form (cancel)="onCancel($event)" [noCluster]="true"></app-add-host>
        <app-add-controls [disabled]="!form.form.valid" (cancel)="!list.length ? onCancel() : (showForm = false)" (save)="save()"></app-add-controls>
      </div>
      <div [style.overflow]="'hidden'" [@openClose]="!(showForm || !list.length)">
        <button mat-raised-button (click)="showForm = true" color="accent"><mat-icon>library_add</mat-icon>&nbsp;Create and add a new host to the cluster</button>
      </div>
      <div [ngClass]="{ hidden: !list.length }">
        <!-- <mat-select
          class="add-host2cluster"
          appInfinityScroll
          (topScrollPoint)="nextPage()"
          (valueChange)="addHost2Cluster(free.value)"
          #free
          placeholder="Select free host and assign to cluster"
        >
          <mat-option>...</mat-option>
          <mat-option *ngFor="let host of list" [value]="host.id" [appTooltip]="host.fqdn" [appTooltipShowByCondition]="true">{{ host.fqdn }}</mat-option>
        </mat-select> -->

        <mat-selection-list class="add-host2cluster" #listHosts (selectionChange)="selectAllHost($event)">
          <mat-list-option *ngIf="list.length"><i>Select all available hosts</i></mat-list-option>
          <mat-list-option *ngFor="let host of list" [value]="host.id" [appTooltip]="host.fqdn" [appTooltipShowByCondition]="true">
            {{ host.fqdn }}
          </mat-list-option>
        </mat-selection-list>
        <p class="controls">
          <button #btn mat-raised-button color="accent" [disabled]="!listHosts?._value?.length" (click)="addHost2Cluster(listHosts._value)">
            Save
          </button>
        </p>
      </div>
    </ng-container>
    <ng-template #load><mat-spinner [diameter]="24"></mat-spinner></ng-template>
  `,
  styles: [
    '.row {display:flex;}',
    '.full { display: flex;padding-left: 6px; margin: 3px 0; justify-content: space-between; } .full>label { vertical-align: middle; line-height: 40px; }',
    '.full:nth-child(odd) {background-color: #4e4e4e;}',
    '.full:hover {background-color: #5e5e5e; }',
    '.add-host2cluster { flex: 1; }',
  ],
  animations: [openClose],
})
export class Host2clusterComponent extends BaseFormDirective implements OnInit, OnDestroy {
  freeHost$: Observable<Host[]>;
  list = [];
  showForm = false;

  page = 0;
  limit = 10;

  @ViewChild('form') hostForm: HostComponent;
  @ViewChild('listHosts')
  private listHosts: MatSelectionList;

  ngOnInit() {
    this.freeHost$ = this.getList();
  }

  getList() {
    return this.service
      .getList<Host>('host', { limit: this.limit, page: this.page, cluster_is_null: 'true' })
      .pipe(tap((list) => (this.list = list)));
  }

  selectAllHost(e: MatSelectionListChange) {
    if (!e.option.value) {
      if (e.option.selected) this.listHosts.selectAll();
      else this.listHosts.deselectAll();
    }
  }

  save() {
    if (this.hostForm.form.valid) {
      const host = this.hostForm.form.value;
      host.cluster_id = this.service.Cluster.id;
      this.service
        .addHost(host)
        .pipe(
          this.takeUntil(),
          tap(() => this.hostForm.form.controls['fqdn'].setValue(''))
        )
        .subscribe();
    }
  }

  addHost2Cluster(value: number[]) {
    this.service
      .addHostInCluster(value.filter((a) => !!a))
      .pipe(
        this.takeUntil(),
        switchMap((_) => (this.freeHost$ = this.getList()))
      )
      .subscribe();
  }

  nextPage() {
    const count = this.list.length;
    if (count === (this.page + 1) * this.limit) {
      this.page++;
      this.service
        .getList<Host>('host', { limit: this.limit, page: this.page, cluster_is_null: 'true' })
        .pipe(this.takeUntil())
        .subscribe((list) => (this.list = [...this.list, ...list]));
    }
  }
}
