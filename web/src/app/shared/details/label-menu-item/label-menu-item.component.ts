import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-label-menu-item',
  template: `
    <a mat-list-item
       routerLinkActive="active"
       [appForTest]="'tab_' + link"
       [routerLink]="link"
    >
      <span>{{ label }}</span>
    </a>
  `,
  styleUrls: ['./label-menu-item.component.scss']
})
export class LabelMenuItemComponent {

  @Input() label: string;
  @Input() link: string;

}
