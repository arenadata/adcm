import { Component, OnInit } from '@angular/core';
import { AdwpCellComponent } from "@adwp-ui/widgets";
import { MatDialog, MatDialogConfig } from "@angular/material/dialog";
import { DialogComponent } from "@app/shared/components";
import { NameEditColumnFieldComponent } from "@app/components/columns/name-edit-column/name-edit-column-field.component";
import { filter } from "rxjs/operators";
import { FormControl, Validators } from "@angular/forms";
import { ListService } from "@app/shared/components/list/list.service";

@Component({
  selector: 'app-name-edit-column',
  templateUrl: './name-edit-column.component.html',
  styleUrls: ['./name-edit-column.component.scss']
})
export class NameEditColumnComponent implements AdwpCellComponent<any>, OnInit {

  row: any;
  column: any;
  form: FormControl;

  constructor(private dialog: MatDialog, protected service: ListService) {}

  ngOnInit() {
    this.form = new FormControl(this.row[this.column.sort],
      [
        Validators.required,
        Validators.maxLength(253),
        Validators.pattern(new RegExp(/^[A-Za-z0-9]{1}[A-Za-z0-9.-]*$/))
      ]);
  }

  isEditable() {
    return this.row.cluster_id === null && this.row.state === 'created';
  }

  rename(event) {
    this.prepare();
    event.preventDefault();
    event.stopPropagation();
  }

  prepare(): void {
    let dialogModel: MatDialogConfig
    const maxWidth = '1400px';
    const width = '500px';
    const title = 'Edit host';

    this.form.setValue(this.row[this.column.sort]);

    dialogModel =  {
      width,
      maxWidth,
      data: {
        title,
        model: {
          row: this.row,
          column: this.column.sort,
          form: this.form
        },
        component: NameEditColumnFieldComponent,
        controls: ['Save', 'Cancel'],
        disabled: this.getFormStatus,
      },
    };

    this.dialog
      .open(DialogComponent, dialogModel)
      .beforeClosed()
      .pipe(filter((save) => save))
      .subscribe(() => {
        this.service.renameHost(this.column.sort, this.form.value, this.row.id)
          .subscribe((value) => {
            if (value) {
              const colName = this.column.sort;
              this.row[colName] = value[colName];
            }
          });
      });
  }

  getFormStatus = (value) => {
    return value.form.invalid;
  }
}
