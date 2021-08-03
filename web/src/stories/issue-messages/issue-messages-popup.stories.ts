import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

import { IssueMessageService } from '../../app/services/issue-message.service';
import { IssueMessageComponent } from '../../app/components/issue-message/issue-message.component';
import { IssueMessageItemComponent } from '../../app/components/issue-message/issue-message-item/issue-message-item.component';
import { IssueMessagePlaceholderPipe } from '../../app/pipes/issue-message-placeholder.pipe';
import { IssueMessageRefComponent } from '../../app/components/issue-message/issue-message-ref/issue-message-ref.component';
import { IMPlaceholderItemType } from '../../app/models/issue-message';
import { PopoverDirective } from '../../app/directives/popover.directive';
import { ISSUE_MESSAGES_DEFAULT_MOCK, ISSUE_MESSAGES_VERY_LONG_MOCK } from './mock';

export default {
  title: 'ADCM/Issue Messages',
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
        PopoverDirective,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: IssueMessageRefComponent,
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

export const PopUp = Template.bind({});
PopUp.args = ISSUE_MESSAGES_DEFAULT_MOCK;

export const PopUpVeryLongMessage = Template.bind({});
PopUpVeryLongMessage.args = ISSUE_MESSAGES_VERY_LONG_MOCK;
