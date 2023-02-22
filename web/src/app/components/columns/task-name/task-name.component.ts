import { Component, Input } from '@angular/core';
import { AdwpCellComponent, ILinkColumn } from '@app/adwp';
import { BehaviorSubject } from 'rxjs';

import { Task } from '@app/core/types';

@Component({
  selector: 'app-task-name',
  template: `
    <adwp-link-cell
      *ngIf="row.jobs.length === 1; else multi"
      [row]="row"
      [column]="linkColumn"
    ></adwp-link-cell>
    <ng-template #multi>
      <div class="multi-title" (click)="toggleExpand(row)">
        <span>{{ row.action?.display_name || 'unknown' }}</span>
        &nbsp;
        <mat-icon>
          {{ (expandedTask | async) && (expandedTask | async).id === row.id ? 'expand_less' : 'expand_more' }}
        </mat-icon>
      </div>
    </ng-template>
  `,
  styleUrls: ['./task-name.component.scss']
})
export class TaskNameComponent implements AdwpCellComponent<Task> {

  row: Task;

  linkColumn: ILinkColumn<Task> = {
    label: '',
    type: 'link',
    value: (row) => row.action?.display_name || 'unknown',
    url: (row) => `/job/${row.jobs[0].id}`,
  };

  @Input() expandedTask: BehaviorSubject<Task | null>;
  @Input() toggleExpand: (row: Task) => void;

}
