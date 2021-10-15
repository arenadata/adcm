import { Component } from '@angular/core';

import { LeftMenuItem } from '@app/shared/details/left-menu/left-menu.component';
import { DetailComponent } from '@app/shared/details/detail.component';
import { DetailsFactory } from '@app/factories/details.factory';

@Component({
  selector: 'app-group-config-provider-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['./../../../shared/details/detail.component.scss']
})
export class GroupConfigProviderDetailsComponent extends DetailComponent {

  leftMenu: LeftMenuItem[] = [
    DetailsFactory.labelMenuItem('Hosts', 'host'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
  ];

}
