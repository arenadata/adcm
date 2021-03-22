import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AdwpCellComponent } from '@adwp-ui/widgets';

import { IBundle } from '@app/models/bundle';
import { StatusData } from '@app/components/columns/status-column/status-column.component';

@Component({
  selector: 'app-edition-column',
  template: `
    {{ row.edition }}
    <ng-container *ngIf="row.license === 'unaccepted'">
      <button mat-icon-button color="warn" matTooltip="Accept license agreement"
              (click)="clickCell($event, 'license', row)">
        <mat-icon>warning</mat-icon>
      </button>
    </ng-container>
  `,
})
export class EditionColumnComponent implements AdwpCellComponent<IBundle> {

  @Input() row: IBundle;

  @Output() onClick = new EventEmitter<StatusData<IBundle>>();

  clickCell(event: MouseEvent, action: string, row: IBundle): void {
    this.onClick.emit({ event, action, row });
  }

}
