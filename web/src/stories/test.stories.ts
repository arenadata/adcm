import { Meta, moduleMetadata } from '@storybook/angular';
import { NotificationsComponent } from '../app/components/notifications/notifications.component';
import { APP_BASE_HREF, CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { BellComponent } from '../app/components/bell/bell.component';
import { TaskService } from '../app/services/task.service';

export default {
  title: 'Popover',
  decorators: [
    moduleMetadata({
      providers: [
        {
          provide: APP_BASE_HREF,
          useValue: '/',
        },
        TaskService,
      ],
      declarations: [
        NotificationsComponent,
        BellComponent,
      ],
      imports: [
        CommonModule,
        RouterModule.forRoot([], { useHash: true }),
        MatIconModule,
      ],
    }),
  ],
  component: BellComponent,
} as Meta;

export const Primary = () => ({
  // moduleMetadata: modules,
  // template: `
  //   <button appPopover [component]="IssuesComponent">Wow</button>
  // `,
});
