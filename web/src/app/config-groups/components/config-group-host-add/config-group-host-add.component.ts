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
import { ChangeDetectionStrategy, Component, OnInit, ViewChild } from '@angular/core';
import { MatSelectionList, MatSelectionListChange } from '@angular/material/list';
import { Host } from '@app/core/types';
import { Observable } from 'rxjs';

import { BaseFormDirective } from '@app/shared/add-component';
import { MatDialog } from '@angular/material/dialog';
import { ConfigGroupHostAddService } from '../../service';
import { ClusterService } from '@app/core/services/cluster.service';
import { ListResult } from '@app/models/list-result';
import { PageEvent } from '@angular/material/paginator';
import { FormControl, Validators } from '@angular/forms';

@Component({
  selector: 'app-config-group-host-add',
  template: `
    <ng-container [formGroup]="form" *ngIf="list$ | async as list">
      <mat-selection-list #selectionList formControlName="hosts" (selectionChange)="selectAll($event)">
        <mat-list-option *ngIf="list.count">All</mat-list-option>
        <mat-list-option *ngFor="let host of list.results" [value]="host">
          {{ host.fqdn }}
        </mat-list-option>
      </mat-selection-list>
      <mat-paginator *ngIf="list.count" [length]="list.count" [pageSizeOptions]="[10, 25, 50, 100]"
                     [pageIndex]="pageIndex" [pageSize]="pageSize"
                     (page)="pageHandler($event)"></mat-paginator>
      <app-add-controls *ngIf="list.count; else not" [title]="'Add'" [disabled]="!form.valid" (cancel)="onCancel()"
                        (save)="save()"></app-add-controls>
    </ng-container>
    <ng-template #not>
      <p>
        <i>
          There are no new hosts. You config group already has all of them.
        </i>
      </p>
    </ng-template>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AddHostToConfigGroupComponent extends BaseFormDirective implements OnInit {

  pageIndex = 0;
  pageSize = 10;

  list$: Observable<ListResult<Host>>;
  @ViewChild('selectionList')
  private list: MatSelectionList;

  constructor(service: ConfigGroupHostAddService, dialog: MatDialog, private cluster: ClusterService) {
    super(service, dialog);

    this.form.addControl('hosts', new FormControl(null, [Validators.required]));
  }

  ngOnInit(): void {
    this.getAvailableHosts(this.pageIndex, this.pageSize);
  }

  selectAll(e: MatSelectionListChange): void {
    if (!e.option.value) {
      if (e.option.selected) this.list.selectAll();
      else this.list.deselectAll();
    }
  }

  save(): void {
    const groupId = this.service.Current.id;
    const result = this.form.get('hosts')?.value?.filter(Boolean).map(v => ({
      host: +v.id,
      group: groupId
    }));

    this.service
      .add(result)
      .pipe(this.takeUntil())
      .subscribe(() => this.dialog.closeAll());
  }

  getAvailableHosts(pageIndex, pageSize): void {
    const { typeName } = this.cluster.Current;
    this.list$ = this.service.getListResults<Host>(typeName, { limit: pageSize, page: pageIndex });
  }

  pageHandler(pageEvent: PageEvent): void {
    this.pageIndex = pageEvent.pageIndex;
    this.pageSize = pageEvent.pageSize;
    this.getAvailableHosts(this.pageIndex, this.pageSize);
  }
}
