import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

import { IssueMessageComponent } from '../../app/components/issue-message/issue-message.component';
import { IssueMessageService } from '../../app/services/issue-message.service';
import { IssueMessageItemComponent } from '../../app/components/issue-message/issue-message-item/issue-message-item.component';
import { IssueMessagePlaceholderPipe } from '../../app/pipes/issue-message-placeholder.pipe';
import { IssueMessageRefComponent } from '../../app/components/issue-message/issue-message-ref/issue-message-ref.component';
import { ISSUE_MESSAGES_DEFAULT_MOCK, ISSUE_MESSAGES_VERY_LONG_MOCK } from './mock';

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
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: IssueMessageComponent,
  argTypes: {
    message: {
      control: { type: 'object' }
    },
  },
  parameters: {
    docs: {
      page: null
    }
  },
} as Meta;

const Template: Story = args => ({
  props: {
    ...args,
  }
});

export const OnlyMessage = Template.bind({});
OnlyMessage.args = ISSUE_MESSAGES_DEFAULT_MOCK;

export const VeryLongMessage = Template.bind({});
VeryLongMessage.args = ISSUE_MESSAGES_VERY_LONG_MOCK;
