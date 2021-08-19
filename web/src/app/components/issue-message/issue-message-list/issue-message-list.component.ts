import { Component, Input } from '@angular/core';

import { IssueMessage } from '@app/models/issue-message';

@Component({
  selector: 'app-issue-message-list',
  template: `
    <ul>
      <li *ngFor="let message of messages; trackBy: identify">
        <app-issue-message [message]="message"></app-issue-message>
      </li>
    </ul>
  `,
  styleUrls: ['./issue-message-list.component.scss']
})
export class IssueMessageListComponent {

  private ownMessages: IssueMessage[] = [];
  @Input() set messages(messages: IssueMessage[]) {
    this.ownMessages = messages;
  }
  get messages(): IssueMessage[] {
    return this.ownMessages;
  }

  @Input() set data(data: { messages: IssueMessage[] }) {
    if (data?.messages) {
      this.ownMessages = data.messages;
    }
  }

  identify(index: number, item: IssueMessage) {
    return item.id;
  }

}
