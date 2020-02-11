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
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { ApiService } from '@app/core/api';
import { EmmitRow } from '@app/core/types';
import { Observable, of, concat } from 'rxjs';
import { filter, switchMap, switchAll, concatAll, map } from 'rxjs/operators';

import { DialogComponent } from './dialog.component';
import { BaseDirective } from '../directives';

interface UpgradeRow {
  upgradable: boolean;
  upgrade: string;
  issue: any;
}

interface Upgrade {
  id: number;
  name: string;
  description: string;
  do: string;
  upgradable: boolean;
  from_edition: string[];
  license: 'unaccepted' | 'absent';
  license_url: string;
}

@Component({
  selector: 'app-upgrade',
  template: `
    <ng-container *ngIf="row.upgradable && !checkIssue(row.issue); else dumb">
      <button
        [appForTest]="'upgrade_btn'"
        matTooltip="There are a pending upgrades of object here"
        mat-icon-button
        color="warn"
        [matMenuTriggerFor]="menu"
        (click)="$event.stopPropagation()"
      >
        <mat-icon>sync_problem</mat-icon>
      </button>
      <mat-menu #menu="matMenu" [overlapTrigger]="false" xPosition="before">
        <ng-template matMenuContent>
          <button *ngFor="let item of list$ | async" mat-menu-item (click)="runUpgrade(item)">
            <span>{{ item.name || 'No name' }}</span>
          </button>
        </ng-template>
      </mat-menu>
    </ng-container>
    <ng-template #dumb>
      <button mat-icon-button color="primary" [disabled]="true"><mat-icon>sync_disabled</mat-icon></button>
    </ng-template>
  `
})
export class UpgradeComponent extends BaseDirective {
  list$: Observable<Upgrade[]>;
  row: UpgradeRow;

  @Input()
  set dataRow(row: UpgradeRow) {
    this.row = row;
    if (row.upgrade) {
      this.list$ = this.api.get(`${row.upgrade}?ordering=-name`).pipe(filter((list: Upgrade[]) => !!list.length));
    }
  }

  @Output()
  refresh: EventEmitter<EmmitRow> = new EventEmitter<EmmitRow>();

  constructor(private api: ApiService, private dialog: MatDialog) {
    super();
  }

  runUpgrade(item: Upgrade) {
    const license$ = item.license === 'unaccepted' ? this.api.put(`${item.license_url}accept/`, {}) : of();
    const do$ = this.api.post<{ id: number }>(item.do, {});
    this.fork(item)
      .pipe(
        switchMap(text =>
          this.dialog
            .open(DialogComponent, {
              data: {
                title: 'Are you sure you want to upgrade?',
                text,
                disabled: !item.upgradable,
                controls: item.license === 'unaccepted' ? { label: 'Do you accept the license agreement?', buttons: ['Yes', 'No'] } : ['Yes', 'No']
              }
            })
            .beforeClosed()
            .pipe(
              this.takeUntil(),
              filter(yes => yes),
              switchMap(() => concat(license$, do$))
            )
        )
      )
      .subscribe(row => this.refresh.emit({ cmd: 'refresh', row }));
  }

  fork(item: Upgrade) {
    const flag = item.license === 'unaccepted';
    return flag ? this.api.get<{ text: string }>(item.license_url).pipe(map(a => a.text)) : of(item.description);
  }

  checkIssue(issue: any): boolean {
    return issue && !!Object.keys(issue).length;
  }
}
