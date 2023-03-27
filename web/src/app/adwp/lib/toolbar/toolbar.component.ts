import { IMenuItem } from '../models/menu-item';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'adwp-toolbar',
  templateUrl: './toolbar.component.html',
  styleUrls: ['./toolbar.component.scss'],
})
export class ToolbarComponent {
  @Input() crumbs: IMenuItem[];
}
