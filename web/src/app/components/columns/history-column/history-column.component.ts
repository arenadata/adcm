import { Component, OnInit } from '@angular/core';
import { MatDialog, MatDialogConfig } from "@angular/material/dialog";
import { DialogComponent } from "@app/shared/components";
import {
  RbacAuditOperationsHistoryFormComponent
} from "@app/components/rbac/audit-operations-history-form/rbac-audit-operations-history-form.component";

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
    return Object.keys(this?.row?.object_changes)?.length !== 0;
  }

  show(event) {
    this.prepare();
    event.preventDefault();
    event.stopPropagation();
  }

  prepare(): void {
    let dialogModel: MatDialogConfig
    const maxWidth = '800px';
    const width = '600px';
    const title = 'Operation detail';


    dialogModel =  {
      width,
      maxWidth,
      data: {
        title,
        model: {
          row: this.row,
        },
        component: RbacAuditOperationsHistoryFormComponent,
        controls: ['Cancel'],
      },
    };

    this.dialog.open(DialogComponent, dialogModel)
  }
}
