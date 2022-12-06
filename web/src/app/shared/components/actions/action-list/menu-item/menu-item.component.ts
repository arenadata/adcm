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
import { Component, Input, ViewChild } from '@angular/core';
import { IAction } from '@app/core/types/actions';
import { MatMenu } from '@angular/material/menu';

@Component({
  selector: 'app-menu-item',
  styleUrls: ['./menu-item.component.scss'],
  template: ` <mat-menu #menu="matMenu" xPosition="after" yPosition="below" overlapTrigger="false">
    <div mat-menu-item disabled *ngIf="!items?.length; else list">
      <i>No actions</i>
    </div>
    <ng-template #list>
      <ng-container *ngFor="let a of items">
        <div *ngIf="!a.children; else branch" [matTooltip]="a.start_impossible_reason">
          <button
            mat-menu-item
            [disabled]="a.start_impossible_reason !== null"
            [appForTest]="'action_btn'"
            [appActions]="{ cluster: cluster, actions: [a] }"
            >
            <span>{{ a.display_name }}</span>
          </button>
        </div>
        <ng-template #branch>
          <button mat-menu-item [matMenuTriggerFor]="inner.menu">
            <span>{{ a.display_name }}</span>
          </button>
          <app-menu-item #inner [items]="a.children" [cluster]="cluster"></app-menu-item>
        </ng-template>
        </ng-container>
      </ng-template>
  </mat-menu>`,
})
export class MenuItemComponent {
  @Input() items: IAction[] = [];
  @Input() cluster: { id: number; hostcomponent: string };
  @ViewChild('menu', { static: true }) menu: MatMenu;
}
