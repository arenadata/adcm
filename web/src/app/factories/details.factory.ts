import { LeftMenuItem } from '../shared/details/left-menu/left-menu.component';
import { LabelMenuItemComponent } from '../shared/details/left-menu-items/label-menu-item/label-menu-item.component';
import { StatusMenuItemComponent } from '@app/shared/details/left-menu-items/status-menu-item/status-menu-item.component';
import { LogMenuItemComponent } from '@app/shared/details/left-menu-items/log-menu-item/log-menu-item.component';

export class DetailsFactory {

  static labelMenuItem(label: string, link: string): LeftMenuItem {
    return {
      label,
      link,
      component: LabelMenuItemComponent,
    };
  }

  static statusMenuItem(label: string, link: string): LeftMenuItem {
    return {
      label,
      link,
      component: StatusMenuItemComponent,
    };
  }

  static logMenuItem(label: string, link: string, logId: number): LeftMenuItem {
    return {
      label,
      link,
      data: { logId },
      component: LogMenuItemComponent,
    };
  }

}
