import { Component, Input } from '@angular/core';
import { AdwpCellComponent } from '@app/adwp';

import { Task } from '@app/core/types';

@Component({
  selector: 'app-task-objects',
  templateUrl: './task-objects.component.html',
  styleUrls: ['./task-objects.component.scss']
})
export class TaskObjectsComponent implements AdwpCellComponent<Task> {
  row: Task;

  @Input() set object(currentObject: any) {
    if (currentObject) {
      this.row = currentObject;
    }
  }

}
