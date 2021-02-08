import { Component, Input, Output, EventEmitter } from '@angular/core';

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
export class StatusColumnComponent<T> {

  @Input() row: T;

  @Output() onClick = new EventEmitter<StatusData<T>>();

  constructor() { }

  clickCell(event: MouseEvent, action: string, row: T): void {
    console.log(event, action, row);
    this.onClick.emit({ event, action, row });
  }

}
