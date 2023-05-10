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
import { Component, Input } from '@angular/core';
import { CheckLog, LogFile } from '@app/core/types/task-job';

@Component({
  selector: 'app-log-check',
  template: `
    <mat-expansion-panel *ngFor="let item of content; trackBy: trackBy" class="panel" [expanded]="current?.title === item.title">
      <mat-expansion-panel-header>
        <mat-panel-title> <mat-icon *ngIf="item.type === 'group'" color="primary" [style.fontSize.rem]="'1.2'">list</mat-icon> {{ item.title }} </mat-panel-title>
        <mat-panel-description class="item-info">
          <span [ngClass]="{ status: true, accent: item.result, warn: !item.result }">[ {{ item.result ? 'Success' : 'Fails' }} ]</span>
        </mat-panel-description>
      </mat-expansion-panel-header>
      <ng-container *ngIf="item.type === 'group'; else one">
        <p>{{ item.message }}</p>
        <mat-accordion>
          <app-log-check [content]="item.content"></app-log-check>
        </mat-accordion>
      </ng-container>
      <ng-template #one>
        <textarea class="check" [readonly]="true">{{ item.message }}</textarea>
      </ng-template>
    </mat-expansion-panel>
  `,
  styles: [
    `
      .status {
        white-space: nowrap;
      }

      .item-info {
        align-items: center;
        justify-content: flex-end;
      }

      textarea {
        background-color: #424242;
        border: 0;
        color: #fff;
        height: 300px;
        width: 100%;
      }
    `,
  ],
})
export class CheckComponent {
  @Input() content: CheckLog[] = [];
  current: CheckLog;
  trackBy(index: number) {
    return index;
  }
}
