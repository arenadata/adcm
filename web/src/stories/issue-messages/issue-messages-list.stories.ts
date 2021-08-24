import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

import { IssueMessageService } from '../../app/services/issue-message.service';
import { IssueMessageComponent } from '../../app/components/issue-message/issue-message.component';
import { IssueMessageItemComponent } from '../../app/components/issue-message/issue-message-item/issue-message-item.component';
import { IssueMessagePlaceholderPipe } from '../../app/pipes/issue-message-placeholder.pipe';
import { IssueMessageRefComponent } from '../../app/components/issue-message/issue-message-ref/issue-message-ref.component';
import { IssueMessageListComponent } from '../../app/components/issue-message/issue-message-list/issue-message-list.component';
import { ISSUE_MESSAGES_LIST_MOCK } from './mock';

export default {
  title: 'ADCM/Issue messages',
  decorators: [
    moduleMetadata({
      providers: [
        IssueMessageService,
      ],
      declarations: [
        IssueMessageComponent,
        IssueMessageItemComponent,
        IssueMessagePlaceholderPipe,
        IssueMessageRefComponent,
        IssueMessageListComponent,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: IssueMessageListComponent,
  argTypes: {
    messages: {
      control: { type: 'object' }
    },
  },
  parameters: {
    docs: {
      page: null
    }
  },
} as Meta;

const Template: Story = (args) => ({
  props: args,
  template: `<app-issue-message-list [messages]="messages"></app-issue-message-list>`,
});

export const ListOfMessages = Template.bind({});
ListOfMessages.args = ISSUE_MESSAGES_LIST_MOCK;
