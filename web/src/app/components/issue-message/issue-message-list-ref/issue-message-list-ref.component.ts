import { Component, Input } from '@angular/core';

import { IssueMessageListComponent } from '@app/components/issue-message/issue-message-list/issue-message-list.component';
import { IssueMessage } from '@app/models/issue-message';

@Component({
  selector: 'app-issue-message-list-ref',
  template: `
    <button
      appPopover
      mat-icon-button
      color="warn"
      [component]="IssueMessageListComponent"
      [data]="data"
    >
      <mat-icon>priority_hight</mat-icon>
    </button>
  `,
  styleUrls: ['./issue-message-list-ref.component.scss']
})
export class IssueMessageListRefComponent {

  IssueMessageListComponent = IssueMessageListComponent;

  private ownMessages: IssueMessage[];
  @Input() set messages(messages: IssueMessage[]) {
    this.ownMessages = messages;
    this.data = {
      messages,
    };
  }
 data: { messages: IssueMessage[] };

}
