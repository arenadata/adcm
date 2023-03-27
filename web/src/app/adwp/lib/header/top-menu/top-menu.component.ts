import { Component, Input } from '@angular/core';

import { IMenuItem } from '../../models/menu-item';


@Component({
  selector: 'adwp-top-menu',
  templateUrl: './top-menu.component.html',
  styleUrls: ['./top-menu.component.scss'],
})
export class TopMenuComponent{
  @Input() appName = '';
  @Input() logoPath = '';
  @Input() items: IMenuItem[] = [];
}
