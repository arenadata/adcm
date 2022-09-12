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
import {Component, EventEmitter, Input, Output, ViewChild} from '@angular/core';
import { MatMenu } from "@angular/material/menu";

@Component({
  selector: 'filter-list',
  template: `
    <mat-menu #menu="matMenu" xPosition="after" yPosition="below" overlapTrigger="false">
      <div mat-menu-item *ngIf="!filters?.length; else list">
        <i>No filters</i>
      </div>
      <ng-template #list>
        <ng-container *ngFor="let a of filters">
          <div>
            <button mat-menu-item (click)="onClick(a)">
              <span>{{ a.display_name }}</span>
            </button>
          </div>
        </ng-container>
      </ng-template>
    </mat-menu>`,
  styleUrls: ['./filter-list.component.scss']
})
export class FilterListComponent {
  @Input() filters: any[];
  @Input() activeFilters: number[];
  @Output() toggleFilter: EventEmitter<number> = new EventEmitter<number>();
  @ViewChild('menu', {static: true}) menu: MatMenu;

  constructor() {}

  onClick(filter) {
    this.toggleFilter.emit(filter);
  }
}
