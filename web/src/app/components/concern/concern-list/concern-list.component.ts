import { Component, Input } from '@angular/core';

import { ConcernReason } from '@app/models/concern/concern-reason';
import { Concern } from '@app/models/concern/concern';

@Component({
  selector: 'app-concern-list',
  template: `
    <ul>
      <li *ngFor="let concern of concerns">
        <app-concern [concern]="concern"></app-concern>
      </li>
    </ul>
  `,
  styleUrls: ['./concern-list.component.scss']
})
export class ConcernListComponent {

  private ownConcerns: Concern[] = [];
  @Input() set concerns(concerns: Concern[]) {
    this.ownConcerns = concerns;
  }
  get concerns(): Concern[] {
    return this.ownConcerns;
  }

  @Input() set data(data: { concerns: Concern[] }) {
    if (data?.concerns) {
      this.ownConcerns = data.concerns;
    }
  }

}
