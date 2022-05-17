import { Meta, moduleMetadata, Story } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { provideMockStore } from '@ngrx/store/testing';

import { ConcernService } from '../../app/services/concern.service';
import { ConcernComponent } from '../../app/components/concern/concern.component';
import { ConcernItemComponent } from '../../app/components/concern/concern-item/concern-item.component';
import { IssueMessagePlaceholderPipe } from '../../app/pipes/issue-message-placeholder.pipe';
import { ConcernListComponent } from '../../app/components/concern/concern-list/concern-list.component';
import { ISSUE_MESSAGES_LIST_MOCK } from './mock';
import { ConcernListRefComponent } from '../../app/components/concern/concern-list-ref/concern-list-ref.component';
import { PopoverDirective } from '../../app/directives/popover.directive';

export default {
  title: 'ADCM/Concern',
  decorators: [
    moduleMetadata({
      providers: [
        ConcernService,
        provideMockStore({}),
      ],
      declarations: [
        ConcernComponent,
        ConcernItemComponent,
        IssueMessagePlaceholderPipe,
        ConcernListComponent,
        ConcernListRefComponent,
        PopoverDirective,
      ],
      imports: [
        CommonModule,
        MatIconModule,
        MatButtonModule,
      ],
    }),
  ],
  component: ConcernListRefComponent,
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
  template: `<app-concern-list-ref [concerns]="concerns"></app-concern-list-ref>`,
});

export const ListOfMessagesPopup = Template.bind({});
ListOfMessagesPopup.args = ISSUE_MESSAGES_LIST_MOCK;
