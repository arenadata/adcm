import { Component } from '@angular/core';
import { AdwpCellComponent } from '@adwp-ui/widgets';
import { filter, switchMap } from 'rxjs/operators';
import { MatDialog } from '@angular/material/dialog';

import { Job } from '@app/core/types';
import { DialogComponent } from '@app/shared/components';


import { ApiService } from '@app/core/api';

@Component({
  selector: 'app-job-status-column',
  templateUrl: './job-status-column.component.html',
  styleUrls: ['./job-status-column.component.scss']
})
export class JobStatusColumnComponent implements AdwpCellComponent<Job> {

  constructor(
    public dialog: MatDialog,
    private api: ApiService,
  ) {}

  row: Job;

  iconDisplay = {
    created: 'watch_later',
    running: 'autorenew',
    success: 'done',
    failed: 'error',
    aborted: 'block'
  };


  cancelJob() {
    this.dialog
      .open(DialogComponent, {
        data: {
          text: 'Are you sure?',
          controls: ['Yes', 'No'],
        },
      })
      .beforeClosed()
      .pipe(
        filter((yes) => yes),
        switchMap(() => this.api.put(`/api/v1/job/${this.row.id}/cancel/`, {}))
      )
      .subscribe();
  }
}
