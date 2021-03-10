import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-state-column',
  templateUrl: './state-column.component.html',
  styleUrls: ['./state-column.component.scss']
})
export class StateColumnComponent<T> {

  @Input() row: T;

}
