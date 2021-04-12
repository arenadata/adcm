import { Component } from '@angular/core';
import { AdwpCellComponent } from '@adwp-ui/widgets/public-api';
import { Task } from '@app/core/types';

@Component({
  selector: 'app-task-status-column',
  templateUrl: './task-status-column.component.html',
  styleUrls: ['./task-status-column.component.scss']
})
export class TaskStatusColumnComponent implements AdwpCellComponent<Task> {

  row: Task;

  getIcon(status: string) {
    switch (status) {
      case 'aborted':
        return 'block';
      default:
        return 'done_all';
    }
  }

  cancelTask(url: string) {
    
  }

}
