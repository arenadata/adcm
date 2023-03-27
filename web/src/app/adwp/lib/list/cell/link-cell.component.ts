import { Component, Input } from '@angular/core';

import { ILinkColumn } from '../../models/list';

@Component({
  selector: 'adwp-link-cell',
  template: `
    <a
      *ngIf="row | listValue : column.value"
      [routerLink]="row | calcLinkCell : column.url"
      class="link"
      (click)="clickOnLink($event)"
    >
      {{ row | listValue : column.value }}
    </a>
  `,
  styles: [`
    :host {
      width: 100%;
      height: 100%;
      display: block;
      box-sizing: border-box;
    }

    .link {
      border-radius: 8px;
      padding: 4px;
      text-decoration: none;
      width: 100%;
      height: 100%;
      display: block;
      box-sizing: border-box;
    }

    .link:hover {
      background: #424242;
    }
  `]
})
export class LinkCellComponent<T> {

  @Input() row: any;
  @Input() column: ILinkColumn<T>;

  clickOnLink(event: MouseEvent): void {
    if (event && event.stopPropagation) {
      event.stopPropagation();
    }
  }

}
