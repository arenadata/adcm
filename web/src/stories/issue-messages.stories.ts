import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';

import { IssueMessageComponent } from '../app/components/issue-message/issue-message.component';
import { IssueMessageService } from '../app/services/issue-message.service';
import { IMPlaceholderItemType } from '../app/models/issue-message';
import { IssueMessageItemComponent } from '../app/components/issue-message/issue-message-item/issue-message-item.component';
import { IssueMessagePlaceholderPipe } from '../app/pipes/issue-message-placeholder.pipe';
import { MatButtonModule } from '@angular/material/button';

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

export const Default = Template.bind({});
Default.args = {
  message: {
    message: 'Run ${action1} action on ${component1}.',
    id: 2039,
    placeholder: {
      action1: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids : {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: 'Restart'
      },
      component1: {
        type: IMPlaceholderItemType.ComponentConfig,
        ids : {
          cluster: 1,
          service: 2,
          component: 2
        },
        name: 'My Component'
      }
    }
  }
};

export const VeryLongMessage = Template.bind({});
VeryLongMessage.args = {
  message: {
    message: 'Run ${action1} action on ${component1}. This is a very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' very very very very very very very very very very very very very very very very very very very very very very very' +
      ' long message. Bonus ${action2}!',
    id: 2039,
    placeholder: {
      action1: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids : {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: 'Restart'
      },
      component1: {
        type: IMPlaceholderItemType.ComponentConfig,
        ids : {
          cluster: 1,
          service: 2,
          component: 2
        },
        name: 'My Component'
      },
      action2: {
        type: IMPlaceholderItemType.ComponentActionRun,
        ids: {
          cluster: 1,
          service: 2,
          component: 2,
          action: 22
        },
        name: ''
      }
    }
  }
};
