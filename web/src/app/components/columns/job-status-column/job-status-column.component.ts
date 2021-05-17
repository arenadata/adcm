import { Component } from '@angular/core';
import { AdwpCellComponent } from '@adwp-ui/widgets';

import { Job } from '@app/core/types';

@Component({
  selector: 'app-job-status-column',
  template: `
    <mat-icon [ngClass]="{ 'icon-locked': row.status === 'running' }" [class]="row.status" [matTooltip]="row.status">
      {{ iconDisplay[row.status] }}
    </mat-icon>
  `,
  styleUrls: ['./job-status-column.component.scss']
})
export class JobStatusColumnComponent implements AdwpCellComponent<Job> {

  row: Job;

  iconDisplay = {
    created: 'watch_later',
    running: 'autorenew',
    success: 'done',
    failed: 'error',
    aborted: 'block'
  };

}
