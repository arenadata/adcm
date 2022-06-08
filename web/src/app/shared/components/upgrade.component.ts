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
import { EmmitRow, IActionParameter, IUIOptions } from '@app/core/types';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';
import { EventHelper } from '@adwp-ui/widgets';
import { BaseDirective } from '../directives';
import { IIssues } from '@app/models/issue';
import { IssueHelper } from '@app/helpers/issue-helper';
import { IConfig } from "@app/shared/configuration/types";

export interface UpgradeItem {
  upgradable: boolean;
  upgrade: string;
  issue: IIssues;
}

export interface Upgrade {
  id: number;
  bundle_id: number;
  name: string;
  description: string;
  do: string;
  upgradable: boolean;
  from_edition: string[];
  license: 'unaccepted' | 'absent';
  license_url: string;
  max_strict: boolean;
  max_version: string;
  min_strict: boolean;
  min_version: string;
  state_available: string;
  state_on_success: string;
  url: string;
  config: IConfig;
  hostcomponentmap: IActionParameter[];
  ui_options: IUIOptions;
}

@Component({
  selector: 'app-upgrade',
  template: `
    <button mat-icon-button
            matTooltip="There are a pending upgrades of object here"
            [appForTest]="'upgrade_btn'"
            color="warn"
            [disabled]="!checkIssue()"
            [matMenuTriggerFor]="menu"
            (click)="EventHelper.stopPropagation($event)"
    >
      <mat-icon>sync_problem</mat-icon>
    </button>
    <mat-menu #menu="matMenu" [overlapTrigger]="false" [xPosition]="xPosition" yPosition="below">
      <ng-template matMenuContent>
        <button *ngFor="let item of list$ | async" mat-menu-item [appUpgrades]="item"> <!--(click)="runUpgrade(item)"-->
          <span>{{ item.name || 'No name' }}</span>
        </button>
      </ng-template>
    </mat-menu>
  `
})
export class UpgradeComponent {
  EventHelper = EventHelper;

  list$: Observable<Upgrade[]>;
  pRow: UpgradeItem = { upgradable: false, upgrade: '', issue: null };

  @Input() xPosition = 'before';

  @Input()
  set row(row: UpgradeItem) {
    this.pRow = row;
    this.list$ = this.getUpgrades(this.pRow.upgrade);
  }

  @Output()
  refresh: EventEmitter<EmmitRow> = new EventEmitter<EmmitRow>();

  constructor(private api: ApiService) {}

  checkIssue() {
    return this.pRow.upgradable && !IssueHelper.isIssue(this.pRow.issue);
  }

  getUpgrades(upgrade: string): Observable<any> {
    return this.api.get(`${upgrade}?ordering=-name`).pipe(
      filter((list: Upgrade[]) => !!list.length)
    );
  }
}
