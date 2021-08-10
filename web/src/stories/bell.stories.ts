import { Meta, moduleMetadata } from '@storybook/angular';
import { APP_BASE_HREF, CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { provideMockStore } from '@ngrx/store/testing';
import { HttpClientModule } from '@angular/common/http';

import { NotificationsComponent } from '../app/components/notifications/notifications.component';
import { BellComponent } from '../app/components/bell/bell.component';
import { TaskService } from '../app/services/task.service';
import { ApiService } from '../app/core/api';
import { AuthService } from '../app/core/auth/auth.service';
import { PopoverDirective } from '../app/directives/popover.directive';

export default {
  title: 'ADCM/Custom Components',
  decorators: [
    moduleMetadata({
      providers: [
        {
          provide: APP_BASE_HREF,
          useValue: '/',
        },
        TaskService,
        ApiService,
        AuthService,
        provideMockStore({}),
      ],
      declarations: [
        NotificationsComponent,
        BellComponent,
        PopoverDirective,
      ],
      imports: [
        CommonModule,
        RouterModule.forRoot([], { useHash: true }),
        MatIconModule,
        HttpClientModule,
      ],
    }),
  ],
  component: BellComponent,
  parameters: {
    docs: {
      page: null
    }
  },
} as Meta;

export const Bell = () => ({ });
