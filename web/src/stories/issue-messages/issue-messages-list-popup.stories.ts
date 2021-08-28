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
import { IssueMessageListRefComponent } from '../../app/components/issue-message/issue-message-list-ref/issue-message-list-ref.component';
import { PopoverDirective } from '../../app/directives/popover.directive';

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
        IssueMessageListRefComponent,
        PopoverDirective,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: IssueMessageListRefComponent,
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
  template: `<app-issue-message-list-ref [messages]="messages"></app-issue-message-list-ref>`,
});

export const ListOfMessagesPopup = Template.bind({});
ListOfMessagesPopup.args = ISSUE_MESSAGES_LIST_MOCK;
