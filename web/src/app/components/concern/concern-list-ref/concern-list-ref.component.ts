import { Component, Input } from '@angular/core';

import { ConcernListComponent } from '@app/components/concern/concern-list/concern-list.component';
import { Concern } from '@app/models/concern/concern';

@Component({
  selector: 'app-concern-list-ref',
  template: `
    <button
      appPopover
      mat-icon-button
      color="warn"
      [component]="ConcernListComponent"
      [data]="data"
      [hideTimeout]="200"
    >
      <mat-icon>priority_hight</mat-icon>
    </button>
  `,
  styleUrls: ['./concern-list-ref.component.scss']
})
export class ConcernListRefComponent {

  ConcernListComponent = ConcernListComponent;

  private ownConcerns: Concern[];
  @Input() set concerns(concerns: Concern[]) {
    this.ownConcerns = concerns;
    this.data = {
      concerns,
    };
  }
  data: { concerns: Concern[] };

}
