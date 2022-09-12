import { Component, Input } from '@angular/core';
import { ConcernService } from '@app/services/concern.service';
import { Concern } from '@app/models/concern/concern';

@Component({
  selector: 'app-concern',
  templateUrl: './concern.component.html',
  styleUrls: ['./concern.component.scss']
})
export class ConcernComponent {

  private ownConcern: Concern;
  @Input() set concern(concern: Concern) {
    this.ownConcern = concern;
    if (this.concern) {
      this.preparedMessage = this.concernService.parse(this.concern.reason.message);
    }
  }
  get concern(): Concern {
    return this.ownConcern;
  }

  @Input() set data(data: { concern: Concern }) {
    if (data?.concern) {
      this.ownConcern = data.concern;
      this.preparedMessage = this.concernService.parse(this.concern.reason.message);
    }
  }

  preparedMessage: string[];

  constructor(
    private concernService: ConcernService,
  ) { }

}
