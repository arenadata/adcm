import { Component, Input } from '@angular/core';
import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';
import { BaseEntity } from '@app/core/types';

@Component({
  selector: 'app-concern-menu-item',
  template: `
    <a mat-list-item
       [appForTest]="'tab_' + link"
       [routerLink]="link"
       routerLinkActive="active"
    >
      <span>{{ label }}</span>&nbsp;
      <ng-container *ngIf="entity | concernMenuItem : data.cause">
        <mat-icon color="warn">
          error_outline
        </mat-icon>
      </ng-container>
    </a>
  `,
  styles: ['a span { white-space: nowrap; }'],
})
export class ConcernMenuItemComponent extends MenuItemAbstractDirective<BaseEntity> {

  @Input() set entity(entity: BaseEntity) {
    this._entity = entity;
  }

  get entity(): BaseEntity {
    return this._entity;
  }

}
