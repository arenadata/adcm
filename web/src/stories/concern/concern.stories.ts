import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

import { ConcernComponent } from '../../app/components/concern/concern.component';
import { ConcernService } from '../../app/services/concern.service';
import { ConcernItemComponent } from '../../app/components/concern/concern-item/concern-item.component';
import { IssueMessagePlaceholderPipe } from '../../app/pipes/issue-message-placeholder.pipe';
import { ISSUE_MESSAGES_DEFAULT_MOCK, ISSUE_MESSAGES_VERY_LONG_MOCK } from './mock';

export default {
  title: 'ADCM/Concern',
  decorators: [
    moduleMetadata({
      providers: [
        ConcernService,
      ],
      declarations: [
        ConcernComponent,
        ConcernItemComponent,
        IssueMessagePlaceholderPipe,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: ConcernComponent,
  argTypes: {
    concern: {
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
