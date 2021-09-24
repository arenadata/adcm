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

@Component({
  selector: 'app-config-group-host-add',
  template: `
    <ng-container *ngIf="list$ | async as list">
      <mat-selection-list #selectionList (selectionChange)="selectAll($event)">
        <mat-list-option *ngIf="list.count">All</mat-list-option>
        <mat-list-option [selected]="selected[host.id]" *ngFor="let host of list.results" [value]="host">
          {{ host.fqdn }}
        </mat-list-option>
      </mat-selection-list>
      <mat-paginator *ngIf="list.count" [length]="list.count" [pageSizeOptions]="[10, 25, 50, 100]"
                     [pageIndex]="pageIndex" [pageSize]="pageSize"
                     (page)="pageHandler($event)"></mat-paginator>
      <app-add-controls *ngIf="list.count; else not" [title]="'Add'" [disabled]="disabled" (cancel)="onCancel()"
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

  selected: { [key: number]: boolean } = {};

  get disabled() {
    return !Object.keys(this.selected).length;
  }

  pageIndex = 0;
  pageSize = 10;

  list$: Observable<ListResult<Host>>;
  @ViewChild('selectionList')
  private list: MatSelectionList;

  constructor(service: ConfigGroupHostAddService, dialog: MatDialog, private cluster: ClusterService) {
    super(service, dialog);
  }

  ngOnInit(): void {
    this.getAvailableHosts(this.pageIndex, this.pageSize);
  }

  selectAll(e: MatSelectionListChange): void {
    const value = e.option.value;
    if (!value) {
      if (e.option.selected) {
        this.list.selectAll();
        this.list.options.filter((o) => !!o.value).forEach((o) => {
          this.selected[o.value.id] = true;
        });

      } else {
        this.list.deselectAll();

        this.list.options.filter((o) => !!o.value).forEach((o) => {
          if (this.selected[o.value.id]) {
            delete this.selected[o.value.id];
          }
        });
      }
    } else {
      if (this.selected[value.id]) {
        delete this.selected[value.id];
      } else {
        this.selected[value.id] = true;
      }
    }
  }

  save(): void {
    const groupId = this.service.Current.id;
    const result = Object.entries(this.selected).map(([id]) => ({
      host: +id,
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
