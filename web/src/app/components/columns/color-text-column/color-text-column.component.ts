import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-color-text-column',
  templateUrl: './color-text-column.component.html',
  styleUrls: ['./color-text-column.component.scss']
})
export class ColorTextColumnComponent implements OnInit {

  row: any;
  column: any;

  red = ['delete', 'failed'];
  orange = ['update'];
  green = ['create', 'success'];

  constructor() {}

  get columnName(): string {
    return this.column?.label?.toLowerCase()?.replace(' ', '_');
  }

  ngOnInit(): void {}

  getColorClass() {
    const value = this.row[this.columnName];

    if (this.red.includes(value)) {
      return 'red';
    } else if (this.orange.includes(value)) {
      return 'orange';
    } else if (this.green.includes(value)) {
      return 'green';
    }
  }

}
