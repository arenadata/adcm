import { Component, OnInit } from '@angular/core';
import { MatDialog } from "@angular/material/dialog";

@Component({
  selector: 'app-history-column',
  templateUrl: './history-column.component.html',
  styleUrls: ['./history-column.component.scss']
})
export class HistoryColumnComponent implements OnInit {

  row: any;

  constructor(private dialog: MatDialog) { }

  ngOnInit(): void {}

  hasChangesHistory() {
    return Object.keys(this?.row?.object_changes)?.length === 0;
  }

  show(event) {
    this.prepare();
    event.preventDefault();
    event.stopPropagation();
  }

  prepare() {
    console.log(this);
  }

}
