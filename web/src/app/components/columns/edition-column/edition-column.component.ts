import { Component, Input, Output } from '@angular/core';
import { AdwpCellComponent } from '@app/adwp';

import { IBundle } from '@app/models/bundle';

@Component({
  selector: 'app-edition-column',
  template: `
    {{ row.edition }}
    <ng-container *ngIf="row.license === 'unaccepted'">
      <button mat-icon-button color="warn" matTooltip="Accept license agreement"
              (click)="onClick({ event: $event, action: 'license', row: row })">
        <mat-icon>warning</mat-icon>
      </button>
    </ng-container>
  `,
  styleUrls: ['./edition-column.component.scss']
})
export class EditionColumnComponent implements AdwpCellComponent<IBundle> {

  @Input() row: IBundle;

  @Output() onClick: (data: { event: MouseEvent, action: string, row: any }) => void;

}
