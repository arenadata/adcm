import { Component, Input } from '@angular/core';

import { NavItem } from '@app/shared/details/navigation.service';

@Component({
  selector: 'app-left-menu',
  templateUrl: './left-menu.component.html',
  styleUrls: ['./left-menu.component.scss']
})
export class LeftMenuComponent {

  @Input() items: NavItem[] = [];

}
