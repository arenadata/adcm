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
import { Component, EventEmitter, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatSelectionList } from '@angular/material/list';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { openClose } from '@app/core/animations';
import { Host } from '@app/core/types';

import { BaseFormDirective } from './base-form.directive';
import { HostComponent } from './host.component';
import { DisplayMode } from './provider.component';

@Component({
  selector: 'app-add-host2cluster',
  template: `
    <div [@openClose]="showForm" [style.overflow]="'hidden'">
      <app-add-host #form [displayMode]="1"></app-add-host>
      <app-add-controls [title]="'Create and add'" [disabled]="!form.form.valid" (cancel)="!Count ? onCancel() : (showForm = false)" (save)="save()"></app-add-controls>
    </div>

    <div [@openClose]="!showForm" [style.overflow]="'hidden'">
      <div class="tools">
        <button
          mat-icon-button
          (click)="showForm = !showForm"
          [color]="showForm ? 'primary' : 'accent'"
          [matTooltip]="showForm ? 'Hide the form for creating and adding a host' : 'Show the form for creating and adding a host'"
        >
          <mat-icon>{{ showForm ? 'clear' : 'add' }}</mat-icon>
        </button>
        &nbsp;
        <mat-checkbox [checked]="false" (click)="selectAllHost(cb.checked)" #cb [matTooltip]="cb.checked ? 'Deselect all' : 'Select all'"></mat-checkbox>
      </div>
      <mat-selection-list class="add-host2cluster" #listHosts>
        <mat-list-option *ngFor="let host of list" [value]="host.id" [appTooltip]="host.fqdn" [appTooltipShowByCondition]="true">
          {{ host.fqdn }}
        </mat-list-option>
      </mat-selection-list>
      <mat-paginator *ngIf="Count" [length]="Count" [pageSizeOptions]="[10, 25, 50, 100]" (page)="pageHandler($event)"></mat-paginator>
      <app-add-controls *ngIf="Count" [title]="'Add'" [disabled]="!listHosts?._value?.length" (cancel)="onCancel()" (save)="addHost2Cluster(listHosts._value)"></app-add-controls>
    </div>
  `,
  styles: ['.add-host2cluster { flex: 1; }', '.tools {text-align: right; margin-right: 16px;}'],
  animations: [openClose],
})
export class Host2clusterComponent extends BaseFormDirective implements OnInit, OnDestroy {
  list: Host[] = [];
  showForm = false;
  Count = 0;
  displayMode: DisplayMode = DisplayMode.default;  
  @Output() event = new EventEmitter();
  @ViewChild('form') hostForm: HostComponent;
  @ViewChild('listHosts') listHosts: MatSelectionList;
  @ViewChild('cb') allCbx: MatCheckbox;
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
        this.displayMode = r.count > 0 ? 2 : 1;
        this.list = r.results;
        if (this.listHosts?.options.length) this.allCbx.checked = false;
      });
  }

  selectAllHost(flag: boolean) {
    if (!flag) this.listHosts.selectAll();
    else this.listHosts.deselectAll();
  }

  save() {
    if (this.hostForm.form.valid) {
      const host = this.hostForm.form.value;
      host.cluster_id = this.service.Cluster.id;
      this.service
        .addHost(host)
        .pipe(this.takeUntil())
        .subscribe((a) => {
          this.hostForm.form.controls['fqdn'].setValue('');
          this.event.emit(`Host [ ${a.fqdn} ] has been added successfully.`);
        });
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
