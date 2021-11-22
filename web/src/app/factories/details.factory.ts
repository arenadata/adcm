import { LeftMenuItem } from '../shared/details/left-menu/left-menu.component';
import { LabelMenuItemComponent } from '../shared/details/left-menu-items/label-menu-item/label-menu-item.component';
import { StatusMenuItemComponent } from '@app/shared/details/left-menu-items/status-menu-item/status-menu-item.component';
import { LogMenuItemComponent } from '@app/shared/details/left-menu-items/log-menu-item/log-menu-item.component';
import { TypeName } from '@app/core/types';
import { ConcernMenuItemComponent } from '@app/shared/details/left-menu-items/concern-menu-item/concern-menu-item.component';
import { ConcernEventType } from '@app/models/concern/concern-reason';

export class DetailsFactory {

  static labelMenuItem(label: string, link: string): LeftMenuItem {
    return {
      label,
      link,
      component: LabelMenuItemComponent,
    };
  }

  static concernMenuItem(label: string, link: string, cause: string, type: ConcernEventType, owner_type: TypeName): LeftMenuItem {
    return {
      label,
      link,
      data: { cause, type, owner_type },
      component: ConcernMenuItemComponent,
    };
  }

  static statusMenuItem(label: string, link: string, entityType: TypeName): LeftMenuItem {
    return {
      label,
      link,
      data: { entityType },
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
