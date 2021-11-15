import { Component } from '@angular/core';

import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';

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
  styles: ['a span { white-space: nowrap; }'],
})
export class LabelMenuItemComponent extends MenuItemAbstractDirective {}
