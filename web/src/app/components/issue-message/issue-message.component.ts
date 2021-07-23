import { Component, Input } from '@angular/core';

import { IssueMessage } from '@app/models/issue-message';
import { IssueMessageService } from '@app/services/issue-message.service';

@Component({
  selector: 'app-issue-message',
  templateUrl: './issue-message.component.html',
  styleUrls: ['./issue-message.component.scss']
})
export class IssueMessageComponent {

  private ownMessage: IssueMessage;
  @Input() set message(message: IssueMessage) {
    this.ownMessage = message;
    this.preparedMessage = this.issueMessageService.parse(this.message.message);
  }
  get message(): IssueMessage {
    return this.ownMessage;
  }

  preparedMessage: string[];

  constructor(
    private issueMessageService: IssueMessageService,
  ) { }

}
