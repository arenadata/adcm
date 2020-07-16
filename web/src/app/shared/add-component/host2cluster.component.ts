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
import { MatSelectionList, MatSelectionListChange } from '@angular/material/list';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { openClose } from '@app/core/animations';
import { Host } from '@app/core/types';

import { BaseFormDirective } from './base-form.directive';
import { HostComponent } from './host.component';

@Component({
  selector: 'app-add-host2cluster',
  template: `
    <p></p>
    <div [@openClose]="showForm">
      <app-add-host #form (cancel)="onCancel()" [noCluster]="true"></app-add-host>
      <app-add-controls [disabled]="!form.form.valid" (cancel)="!Count ? onCancel() : (showForm = false)" (save)="save()"></app-add-controls>
    </div>
    <mat-selection-list class="add-host2cluster" #listHosts (selectionChange)="selectAllHost($event)">
      <mat-list-option *ngIf="list.length > 1"><i>Select all available hosts</i></mat-list-option>
      <mat-list-option *ngFor="let host of list" [value]="host.id" [appTooltip]="host.fqdn" [appTooltipShowByCondition]="true">
        {{ host.fqdn }}
      </mat-list-option>
    </mat-selection-list>
    <mat-paginator *ngIf="Count" [length]="Count" [pageSizeOptions]="[10, 25, 50, 100]" (page)="pageHandler($event)"></mat-paginator>
    <div class="bottom-controls">
      <button [@openClose]="!showForm" mat-raised-button (click)="showForm = true" color="accent">Create</button>
      <app-add-controls *ngIf="Count" [disabled]="!listHosts?._value?.length" (cancel)="onCancel()" (save)="addHost2Cluster(listHosts._value)"></app-add-controls>
    </div>
  `,
  styles: ['.add-host2cluster { flex: 1; }', '.bottom-controls {display: flex; justify-content: space-between; align-items: center;}'],
  animations: [openClose],
})
export class Host2clusterComponent extends BaseFormDirective implements OnInit, OnDestroy {
  list: Host[] = [];
  showForm = false;
  Count = 0;

  @ViewChild('form') hostForm: HostComponent;
  @ViewChild('listHosts') listHosts: MatSelectionList;
  @ViewChild(MatPaginator) paginator: MatPaginator;

  ngOnInit() {
    this.getAvailableHosts();
  }

  getAvailableHosts(pageIndex = 0, pageSize = 10) {
    this.service
      .getListResults<Host>('host', { limit: pageSize, page: pageIndex, cluster_is_null: 'true' })
      .pipe(this.takeUntil())
      .subscribe((r) => {
        this.Count = r.count;
        this.showForm = !r.count;
        this.list = r.results;
        if (this.listHosts?.options.length) this.listHosts.options.first.selected = false;
      });
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
        .pipe(this.takeUntil())
        .subscribe(() => this.hostForm.form.controls['fqdn'].setValue(''));
    }
  }

  addHost2Cluster(value: number[]) {
    this.service
      .addHostInCluster(value.filter((a) => !!a))
      .pipe(this.takeUntil())
      .subscribe(() => this.getAvailableHosts());
  }

  pageHandler(pageEvent: PageEvent) {
    this.getAvailableHosts(pageEvent.pageIndex, pageEvent.pageSize);
  }
}
