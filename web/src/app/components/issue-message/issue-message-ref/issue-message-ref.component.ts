import { Component, Input } from '@angular/core';

import { IssueMessageComponent } from '@app/components/issue-message/issue-message.component';
import { IssueMessage } from '@app/models/issue-message';

@Component({
  selector: 'app-issue-message-ref',
  templateUrl: './issue-message-ref.component.html',
  styleUrls: ['./issue-message-ref.component.scss']
})
export class IssueMessageRefComponent {

  IssueMessageComponent = IssueMessageComponent;

  @Input() message: IssueMessage;
  @Input() data: { messages: IssueMessage };


}
