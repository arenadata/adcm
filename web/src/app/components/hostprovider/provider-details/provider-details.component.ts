import { Component } from '@angular/core';

import { DetailComponent } from '@app/shared/details/detail.component';
import { LeftMenuItem } from '@app/shared/details/left-menu/left-menu.component';
import { DetailsFactory } from '@app/factories/details.factory';

@Component({
  selector: 'app-provider-details',
  templateUrl: '../../../templates/details.html',
  styleUrls: ['./../../../shared/details/detail.component.scss']
})
export class ProviderDetailsComponent extends DetailComponent {

  leftMenu: LeftMenuItem[] = [
    DetailsFactory.labelMenuItem('Main', 'main'),
    DetailsFactory.labelMenuItem('Configuration', 'config'),
    DetailsFactory.labelMenuItem('Configuration groups', 'group_config'),
  ];

}
