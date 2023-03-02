import { Component, Input, Output, EventEmitter } from '@angular/core';
import { AdwpCellComponent } from '@app/adwp';

export interface StatusData<T> {
  event: MouseEvent;
  action: string;
  row: T;
}

@Component({
  selector: 'app-status-column',
  templateUrl: './status-column.component.html',
  styleUrls: ['./status-column.component.scss']
})
export class StatusColumnComponent<T> implements AdwpCellComponent<T> {

  @Input() row: T;

  @Output() onClick = new EventEmitter<StatusData<T>>();

  clickCell(event: MouseEvent, action: string, row: T): void {
    this.onClick.emit({ event, action, row });
  }

}
