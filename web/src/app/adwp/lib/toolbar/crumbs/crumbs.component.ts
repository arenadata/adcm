import { IMenuItem } from './../../models/menu-item';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'adwp-crumbs',
  templateUrl: './crumbs.component.html',
  styleUrls: ['./crumbs.component.scss'],
})
export class CrumbsComponent {
  @Input() navigation: IMenuItem[];
}
