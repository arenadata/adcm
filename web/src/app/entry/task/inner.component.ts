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
import { Job } from '@app/core/types';

@Component({
  selector: 'app-task-inner',
  template: `
    <table mat-table [dataSource]="dataSource" class="inner">
      <ng-container matColumnDef="job_name">
        <td mat-cell *matCellDef="let row">
          <span *ngIf="row.status === 'created'; else joblink" class="created">{{ row.display_name || row.id }}</span>
          <ng-template #joblink>
            <a [routerLink]="['/job', row.id]">{{ row.display_name || row.id }}</a>
          </ng-template>
        </td>
      </ng-container>
      <ng-container matColumnDef="start_date_job">
        <td mat-cell *matCellDef="let row" class="action_date">
          {{ row.status !== 'created' ? (row.start_date | date: 'medium') : '' }}
        </td>
      </ng-container>
      <ng-container matColumnDef="finish_date_job">
        <td mat-cell *matCellDef="let row" class="action_date padding20">
          {{ row.status === 'success' || row.status === 'failed' ? (row.finish_date | date: 'medium') : '' }}
        </td>
      </ng-container>
      <ng-container matColumnDef="status_job">
        <td mat-cell *matCellDef="let row" class="end center">
          <mat-icon [ngClass]="{ 'icon-locked': row.status === 'running' }" [class]="row.status" [matTooltip]="row.status">
            {{ iconDisplay[row.status] }}
          </mat-icon>
        </td>
      </ng-container>
      <tr mat-row *matRowDef="let row; columns: displayColumns"></tr>
    </table>
  `,
  styleUrls: ['./task.component.scss']
})
export class InnerComponent {
  displayColumns = ['job_name', 'start_date_job', 'finish_date_job', 'status_job'];
  
  @Input() dataSource: Job[];

  iconDisplay = {
    created: 'watch_later',
    running: 'autorenew',
    success: 'done',
    failed: 'error',
    aborted: 'block'
  };
}
