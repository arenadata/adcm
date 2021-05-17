import { Component } from '@angular/core';
import { AdwpCellComponent } from '@adwp-ui/widgets/public-api';

import { Task } from '@app/core/types';

@Component({
  selector: 'app-task-objects',
  templateUrl: './task-objects.component.html',
  styleUrls: ['./task-objects.component.scss']
})
export class TaskObjectsComponent implements AdwpCellComponent<Task> {

  row: Task;

}
