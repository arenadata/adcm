import { Component, Input } from '@angular/core';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { IColumns, AdwpComponentHolder } from '@app/adwp';
import { BehaviorSubject } from 'rxjs';

import { Job, Task } from '@app/core/types';
import { DateHelper } from '@app/helpers/date-helper';
import { JobStatusColumnComponent } from '@app/components/columns/job-status-column/job-status-column.component';
import { JobNameComponent } from '@app/components/columns/job-name/job-name.component';

@Component({
  selector: 'app-jobs',
  animations: [
    trigger('jobsExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0' })),
      state('expanded', style({ height: '*' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
  template: `
    <div class="expand-jobs"
         [@jobsExpand]="(expandedTask | async) && (expandedTask | async).id === row.id ? 'expanded' : 'collapsed'">
      <adwp-table *ngIf="row?.jobs?.length > 1"
                  [columns]="columns"
                  [dataSource]="data"
                  headerRowClassName="hidden"
      ></adwp-table>
    </div>
  `,
  styleUrls: ['./jobs.component.scss'],
})
export class JobsComponent<T extends Task> implements AdwpComponentHolder<Task> {

  columns: IColumns<Job> = [
    {
      type: 'component',
      label: '',
      component: JobNameComponent,
    },
    {
      label: '',
      value: (row) => {
        return row.status !== 'created' ? DateHelper.short(row.start_date) : '';
      },
      className: 'action_date',
      headerClassName: 'action_date',
    },
    {
      label: '',
      value: (row) => row.status === 'success' || row.status === 'failed' ? DateHelper.short(row.finish_date) : '',
      className: 'action_date',
      headerClassName: 'action_date',
    },
    {
      label: '',
      type: 'component',
      component: JobStatusColumnComponent,
      className: 'table-end center status',
      headerClassName: 'table-end center status',
    }
  ];

  private ownData: { results: Job[], count: number };
  get data(): { results: Job[], count: number } {
    return this.ownData;
  }

  private ownRow: Task;
  @Input() set row(row: Task) {
    this.ownRow = row;
    this.ownData = { results: this.ownRow?.jobs, count: 0 };
  }
  get row(): Task {
    return this.ownRow;
  }

  @Input() expandedTask: BehaviorSubject<Task>;

}
