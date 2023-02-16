import { Component } from '@angular/core';
import { AdwpCellComponent } from '@adwp-ui/widgets';
import { filter, switchMap, tap } from 'rxjs/operators';
import { MatDialog } from '@angular/material/dialog';

import { Task } from '@app/core/types';
import { DialogComponent } from '@app/shared/components';
import { ApiService } from '@app/core/api';

@Component({
  selector: 'app-task-status-column',
  templateUrl: './task-status-column.component.html',
  styleUrls: ['./task-status-column.component.scss']
})
export class TaskStatusColumnComponent implements AdwpCellComponent<Task> {

  constructor(
    public dialog: MatDialog,
    private api: ApiService,
  ) {}

  row: Task;

  cancelTask(url: string) {
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
        switchMap(() => this.api.put(url, {})
                                .pipe(
                                  tap(()=> this.row.status = 'aborted')
                                )
        )
      )
      .subscribe();
  }

}
