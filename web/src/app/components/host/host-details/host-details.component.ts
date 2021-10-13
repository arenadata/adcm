import { Component } from '@angular/core';

import { DetailComponent } from '@app/shared/details/detail.component';
import { LeftMenuItem } from '@app/shared/details/left-menu/left-menu.component';
import { LabelMenuItemComponent } from '@app/shared/details/label-menu-item/label-menu-item.component';
import { StatusMenuItemComponent } from '@app/shared/details/status-menu-item/status-menu-item.component';

@Component({
  selector: 'app-host-details',
  templateUrl: './host-details.component.html',
  styleUrls: ['./../../../shared/details/detail.component.scss']
})
export class HostDetailsComponent extends DetailComponent {

  leftMenu: LeftMenuItem[] = [
    {
      label: 'Main',
      link: 'main',
      component: LabelMenuItemComponent,
    }, {
      label: 'Configuration',
      link: 'config',
      component: LabelMenuItemComponent,
    }, {
      label: 'Status',
      link: 'status',
      component: StatusMenuItemComponent,
    }
  ];

}
