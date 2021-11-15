import { Component, Input } from '@angular/core';
import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';
import { BaseEntity } from '@app/core/types';
import { selectMessage, SocketState } from '@app/core/store';
import { Store } from '@ngrx/store';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-concern-menu-item',
  template: `
    <a mat-list-item
       [appForTest]="'tab_' + link"
       [routerLink]="link"
       routerLinkActive="active"
    >
      <span>{{ label }}</span>&nbsp;
      <ng-container *ngIf="isConcern">
        <mat-icon color="warn">
          error_outline
        </mat-icon>
      </ng-container>
    </a>
  `,
  styles: ['a span { white-space: nowrap; }'],
})
export class ConcernMenuItemComponent extends MenuItemAbstractDirective<BaseEntity> {

  isConcern = false;

  @Input() set entity(entity: BaseEntity) {
    this._entity = entity;
    this.listenToConcernChanges();
  }

  get entity(): BaseEntity {
    return this._entity;
  }

  constructor(
    private store: Store<SocketState>,
  ) {
    super();
  }

  private listenToConcernChanges() {
    this.store.pipe(
      selectMessage,
      filter(event => event?.object?.id && this.entity?.id && event.object.id === this.entity.id),
      filter(event => event?.event === 'concern'),
      filter(event => event?.object?.details.type === this.data.cause),
      this.takeUntil(),
    ).subscribe((event) => {
      this.isConcern = event.object.details.value;
    });
  }
}
