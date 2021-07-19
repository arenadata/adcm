import { Meta, moduleMetadata } from '@storybook/angular';
import { NotificationsComponent } from '../app/components/notifications/notifications.component';
import { APP_BASE_HREF, CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { BellComponent } from '../app/components/bell/bell.component';
import { TaskService } from '../app/services/task.service';
import { provideMockStore } from '@ngrx/store/testing';
import { ApiService } from '../app/core/api';
import { HttpClientModule } from '@angular/common/http';
import { AuthService } from '../app/core/auth/auth.service';
import { PopoverDirective } from '../app/directives/popover.directive';

export default {
  title: 'Custom components',
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
} as Meta;

export const Bell = () => ({ });
