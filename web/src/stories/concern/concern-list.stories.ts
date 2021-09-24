import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

import { ConcernService } from '../../app/services/concern.service';
import { ConcernComponent } from '../../app/components/concern/concern.component';
import { ConcernItemComponent } from '../../app/components/concern/concern-item/concern-item.component';
import { IssueMessagePlaceholderPipe } from '../../app/pipes/issue-message-placeholder.pipe';
import { ConcernListComponent } from '../../app/components/concern/concern-list/concern-list.component';
import { ISSUE_MESSAGES_LIST_MOCK } from './mock';

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
        ConcernListComponent,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: ConcernListComponent,
  argTypes: {
    concerns: {
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
  template: `<app-concern-list [concerns]="concerns"></app-concern-list>`,
});

export const ListOfMessages = Template.bind({});
ListOfMessages.args = ISSUE_MESSAGES_LIST_MOCK;
