import { Component, Input } from '@angular/core';
import { filter } from 'rxjs/operators';
import { Store } from '@ngrx/store';

import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';
import { BaseEntity } from '@app/core/types';
import { selectMessage, SocketState } from '@app/core/store';

@Component({
  selector: 'app-status-menu-item',
  template: `
    <a mat-list-item
       [appForTest]="'tab_' + link"
       [routerLink]="link"
       routerLinkActive="active"
    >
      <span>{{ label }}</span>&nbsp;
      <ng-container *ngIf="entity">
        <mat-icon [color]="entity.status === 0 ? 'accent' : 'warn'">
          {{ entity.status === 0 ? 'check_circle_outline' : 'error_outline' }}
        </mat-icon>
      </ng-container>
    </a>
  `,
  styles: ['a span { white-space: nowrap; }'],
})
export class StatusMenuItemComponent extends MenuItemAbstractDirective<BaseEntity> {

  @Input() set entity(entity: BaseEntity) {
    this._entity = entity;
    this.listenToStatusChanges();
  }
  get entity(): BaseEntity {
    return this._entity;
  }

  constructor(
    private store: Store<SocketState>,
  ) {
    super();
  }

  listenToStatusChanges() {
    this.store.pipe(
      selectMessage,
      filter(event => event?.object?.id && this.entity?.id && event.object.id === this.entity.id),
      filter(event => event?.event === 'change_status'),
      filter(event => event?.object?.type === this.data.entityType),
      this.takeUntil(),
    ).subscribe((event) => this.entity.status = +event.object.details.value);
  }

}
